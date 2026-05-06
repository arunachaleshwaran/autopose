import bpy
import numpy as np
from mathutils import Vector
ICO_SPHERE_RADIUS = 1

# Add an ico sphere with the specified subdivisions and radius
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=ICO_SPHERE_RADIUS, location=(0, 0, 0))
ico = bpy.context.active_object

if ico is None:
    raise RuntimeError("Failed to create icosphere")

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
    print(bpy.context.scene.render.filepath)
    bpy.ops.render.render(write_still=True)