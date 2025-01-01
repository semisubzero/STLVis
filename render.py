import bpy
import os
from mathutils import Vector, Euler
import math

"""
Hardcoded options
"""
# Path to the STL files
stl_dir = "/Users/brandonramirez/dev/StlViz/inputs"

IMGTYPE = 'JPEG'
HEIGHT = 2001
WIDTH = 2668

# Define tilt angles in degrees and convert to radians
top_tilt_angle = 20   # Tilting camera downwards by 20 degrees
bottom_tilt_angle = -20  # Tilting camera upwards by 20 degrees¬

"""
Setup Scene
"""

# Set render settings
bpy.context.scene.render.image_settings.file_format = IMGTYPE
bpy.context.scene.render.resolution_x = WIDTH
bpy.context.scene.render.resolution_y = HEIGHT

def position_camera(camera, obj, tilt_angle, padding):
    import bpy
    from math import radians, sin, cos
    from mathutils import Vector

    # Get the object's bounding box corners in world coordinates
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    # Calculate the center of the bounding box
    bbox_center = sum(bbox_corners, Vector()) / 8

    # Calculate the maximum distance from the bounding box center to its corners
    max_distance = max((corner - bbox_center).length for corner in bbox_corners)
    
    # This max_distance represents the radius of the bounding sphere around the object
    # Apply padding
    max_radius = max_distance * padding

    # Get the camera's lens data
    cam_data = camera.data

    if cam_data.type != 'PERSP':
        print("Camera must be a perspective camera.")
        return

    # Get the camera's vertical field of view (in radians)
    fov = cam_data.angle_y

    # Calculate the required distance from the object to the camera to fit the entire bounding sphere
    required_distance = max_radius / sin(fov / 2)

    # Convert the tilt angle to radians
    tilt_radians = radians(tilt_angle)

    # Calculate the camera's location
    x = bbox_center.x
    y = bbox_center.y - required_distance * cos(tilt_radians)
    z = bbox_center.z + required_distance * sin(tilt_radians)
    camera.location = (x, y, z)

    # Make the camera look at the center of the bounding box
    direction = bbox_center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    
def find_render_stl_files(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith('.stl'):
                render_stl(os.path.join(dirpath, filename))
    
def render_stl(path):    
    """
    Rotate object and capture renders
    """
    filename = path.split('/')[-1].split('.')[0]
    outdir = '/'.join(path.split('/')[:-1])
    print("Rendering " + filename)
    
    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Import the STL file
    bpy.ops.import_mesh.stl(filepath=path)

    # Get the imported object
    obj = bpy.context.selected_objects[0]
    
    # Set the origin to the geometry's center of mass
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Move the object to the world origin
    obj.location = (0.0, 0.0, 0.0)

    # Calculate the bounding box dimensions
    bpy.context.view_layer.update()
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bbox_min = Vector((min(corner.x for corner in bbox_corners),
                       min(corner.y for corner in bbox_corners),
                       min(corner.z for corner in bbox_corners)))
    bbox_max = Vector((max(corner.x for corner in bbox_corners),
                       max(corner.y for corner in bbox_corners),
                       max(corner.z for corner in bbox_corners)))
    bbox_center = (bbox_min + bbox_max) / 2
    bbox_size = bbox_max - bbox_min

    # Create a camera if it doesn't exist
    if 'Camera' not in bpy.data.objects:
        camera_data = bpy.data.cameras.new(name='Camera')
        camera = bpy.data.objects.new('Camera', camera_data)
        bpy.context.collection.objects.link(camera)
    else:
        camera = bpy.data.objects['Camera']

    # Set the camera as the active camera
    bpy.context.scene.camera = camera

    # Create a new material with a neutral color
    material = bpy.data.materials.new(name="NeutralMaterial")
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)  # Light grey color

    # Assign the material to the object
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

    # Set up a soft directional light
    light_data = bpy.data.lights.new(name="Directional Light", type='SUN')
    light_data.energy = 3  # Adjust energy for softness
    light_object = bpy.data.objects.new(name="Directional Light", object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    light_object.location = (bbox_center.x, bbox_center.y - max(bbox_size), bbox_center.z + max(bbox_size) * 2)
    light_object.rotation_euler = (0.785, 0, 0.785)  # 45 degrees in radians for soft angle
    
    # Rotate and render images top view
    for i in range(4):
        # Rotate the object
        obj.rotation_euler[2] = i * (3.14159 / 2)  # 45 degrees in radians

        # Adjust camera to fit the object
        position_camera(camera, obj, top_tilt_angle, 1)

        # Update the scene
        bpy.context.view_layer.update()

        # Set the output file path
        bpy.context.scene.render.filepath = os.path.join(outdir, f"renders_{filename}/{filename}_top_{obj.rotation_euler[2]}.{IMGTYPE}")

        # Render the image
        bpy.ops.render.render(write_still=True)
        
    # Rotate and render images bottom view
    for i in range(8):
        # Rotate the object
        obj.rotation_euler[2] = i * (3.14159 / 2)  # 45 degrees in radians

        # Adjust camera to fit the object
        position_camera(camera, obj, bottom_tilt_angle, 1)

        # Update the scene
        bpy.context.view_layer.update()

        # Set the output file path
        bpy.context.scene.render.filepath = os.path.join(outdir, f"renders_{filename}/{filename}_bottom_{math.degrees(obj.rotation_euler[2])}.{IMGTYPE}")

        # Render the image
        bpy.ops.render.render(write_still=True)
        
find_render_stl_files(stl_dir)
print("All rendering complete.")