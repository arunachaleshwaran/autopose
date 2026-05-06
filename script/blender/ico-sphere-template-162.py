import bpy
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

# Add an ico sphere with the specified subdivisions and radius
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=max(benchy.dimensions) * CAMERA_POSITION_RANGE, location=(0, 0, 0))
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
elevation = np.arcsin(z)              # radians, [-pi/2, pi/2]
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

for i, v in enumerate(viewpoints):
    cam.location = Vector(v)
    bpy.context.view_layer.update()        # apply the constraint now
    bpy.context.scene.render.filepath = f"//templates/tmpl_{i:03d}.png"
    bpy.ops.render.render(write_still=True)