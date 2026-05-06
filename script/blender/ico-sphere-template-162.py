import bpy
import json
import numpy as np
from mathutils import Vector
from pathlib import Path

CAMERA_POSITION_RANGE = 4
BENCHY_STL = Path(__file__).resolve().parents[2] / "assets" / "3dbenchy.stl"
# BENCHY_STL = "/Users/arunachaleshwaran/Documents/monk/autopose/assets/3dbenchy.stl"

SUBJECT_MAX_DIM = 0.5  # longest axis of the imported model in Blender units

# Clear the default scene (delete all objects)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'

# Import 3DBenchy and center+scale it at the origin
if not BENCHY_STL.exists():
    raise FileNotFoundError(f"STL not found: {BENCHY_STL}")
bpy.ops.wm.stl_import(filepath=str(BENCHY_STL))
benchy = bpy.context.active_object
benchy.name = "Benchy"

bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
benchy.location = (0.0, 0.0, 0.0)

max_dim = max(benchy.dimensions)
if max_dim > 0:
    s = SUBJECT_MAX_DIM / max_dim
    benchy.scale = (s, s, s)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

iso_sphere_radius = max(benchy.dimensions) * CAMERA_POSITION_RANGE
# Add an ico sphere with the specified subdivisions and radius
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=iso_sphere_radius, location=(0, 0, 0))
ico = bpy.context.active_object

if ico is None:
    raise RuntimeError("Failed to create icosphere")

ico.hide_render = True  # icosphere is just a viewpoint source, not part of the render
n = len(ico.data.vertices)
co = np.empty(n * 3, dtype=np.float32)
ico.data.vertices.foreach_get("co", co)
viewpoints = co.reshape(n, 3)         # shape (162, 3) — these are your azimuth+elevation samples

# Convert each to (azimuth, elevation) if you want angles instead of unit vectors
x, y, z = viewpoints.T
elevation = np.arcsin(z / iso_sphere_radius)              # radians, [-pi/2, pi/2]
azimuth   = np.arctan2(y, x)          # radians, [-pi, pi]

# Make / reuse one camera
cam_data = bpy.data.cameras.new("TemplateCam")
cam = bpy.data.objects.new("TemplateCam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

# Empty at the origin — camera tracks it
target = bpy.data.objects.new("Target", None)
bpy.context.collection.objects.link(target)
target.location = (0, 0, 0)

# Track To constraint: -Z forward, +Y up (Blender camera convention)
con = cam.constraints.new(type='TRACK_TO')
con.target = target
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'

# ---- Render settings ----
scene = bpy.context.scene
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = 224
scene.render.resolution_y = 224
scene.render.resolution_percentage = 100
scene.render.filepath = "//templates/tmpl_"  # Blender appends frame number padded to render.frame_padding (default 4)
scene.frame_start = 0
scene.frame_end = n - 1

# ---- Keyframe viewpoint[i] at frame i, then force CONSTANT interpolation (hard cuts) ----
for i, v in enumerate(viewpoints):
    scene.frame_set(i)
    cam.location = Vector(v.tolist())
    cam.keyframe_insert(data_path="location", frame=i)

if cam.animation_data and cam.animation_data.action:
    for fcurve in cam.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'CONSTANT'

# ---- Pose dump: one JSON for all frames (after keyframes so Track To resolves correctly each frame) ----
templates_dir = Path(bpy.path.abspath(scene.render.filepath)).parent
templates_dir.mkdir(parents=True, exist_ok=True)

poses = []
for i in range(n):
    scene.frame_set(i)
    bpy.context.view_layer.update()
    mw = cam.matrix_world
    R_c2w = mw.to_3x3()
    R_w2c = R_c2w.transposed()
    t = mw.translation
    poses.append({
        "frame": i,
        "file": f"tmpl_{i:04d}.png",
        "viewpoint_xyz": viewpoints[i].tolist(),
        "azimuth_rad": float(azimuth[i]),
        "elevation_rad": float(elevation[i]),
        "azimuth_deg": float(np.degrees(azimuth[i])),
        "elevation_deg": float(np.degrees(elevation[i])),
        "R_cam_to_world_3x3": [list(r[:3]) for r in R_c2w],
        "R_world_to_cam_3x3": [list(r[:3]) for r in R_w2c],
        "t_cam_to_world_3": [t.x, t.y, t.z],
    })

(templates_dir / "poses.json").write_text(json.dumps(poses, indent=2))

# ---- Render the full animation: 1 PNG per frame ----
scene.frame_set(scene.frame_start)
bpy.ops.render.render(animation=True)

print(f"Done: {n} templates rendered to {templates_dir}")