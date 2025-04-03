import bpy
import mathutils
import math

# Create Panels and Operators
class VIEW3D_PT_BoneToMeshPanel(bpy.types.Panel):
    bl_label = "Bone To Mesh"
    bl_description = "Create a mesh from the selected bone"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "NOPPERS Tools"

    def draw(self, context):
        layout = self.layout

        # Check if an armature is selected and editor is in Object mode
        bone_to_mesh_enabled = False
        bone_to_mesh_enabled = (context.active_object is not None
                                and context.active_object.type == 'ARMATURE'
                                and context.active_object.mode == 'OBJECT')

        row = layout.row()
        row.enabled = bone_to_mesh_enabled
        row.operator("object.bone_to_mesh",
                     text="Create Mesh",
                     icon='MESH_CUBE')
        
        # Display a message explaining why the button is disabled
        if not bone_to_mesh_enabled:
            info_row = layout.row()
            info_row.alert = True  # Makes the text red for emphasis
            info_row.label(text="Select an armature first",
                           icon='ERROR')

def createMesh(self, context):
    obj = context.active_object

    if obj is None:
        self.report({'ERROR'}, "No selection")
        return False
    elif obj.type != 'ARMATURE':
        self.report({'WARNING'}, "Armature expected")
        return False
    else:
        processArmature(self, context, obj)
        return True

def meshFromArmature(arm):
    name = arm.name + "_mesh"
    meshData = bpy.data.meshes.new(name + "Data")
    meshObj = bpy.data.objects.new(name, meshData)
    meshObj.matrix_world = arm.matrix_world.copy()
    return meshObj

def boneGeometry(l1, l2, x, z, baseSize, l1Size, l2Size, base, roll):
    # Calculate the positions of the surrounding points based on the length of the bone
    bone_length = (l2 - l1).length
    radius = bone_length * 0.15  # Define a radius based on the bone length

    x1 = x * radius
    z1 = z * radius

    # Define the vertices for the octahedral shape
    verts = [
        l1,  # Head
        l2,  # Tail
        l1 + x1,  # Head X+
        l1 - x1,  # Head X-
        l1 + z1,  # Head Z+
        l1 - z1,  # Head Z-
    ]

    # Translate the 4 vertices between head and tail so that they are 10% of the way to the tail
    translation_vector = (l2 - l1) * 0.1
    for i in range(2, len(verts)):
        verts[i] += translation_vector

    # Rotate the vertices around the Head and Tail axis to match the bone's roll
    rotation_matrix = mathutils.Matrix.Rotation(roll, 4, (l2 - l1).normalized())
    
    # Additional 45-degree rotation
    additional_rotation = mathutils.Matrix.Rotation(math.radians(45), 4, (l2 - l1).normalized())
    rotation_matrix @= additional_rotation

    for i in range(2, len(verts)):
        verts[i] = (rotation_matrix @ (verts[i] - l1)) + l1

    # Define the faces for the octahedral shape
    faces = [
        (base, base + 2, base + 4),  # Head X+ Z+
        (base, base + 4, base + 3),  # Head Z+ X-
        (base, base + 3, base + 5),  # Head X- Z-
        (base, base + 5, base + 2),  # Head Z- X+
        (base + 1, base + 2, base + 4),  # Tail X+ Z+
        (base + 1, base + 4, base + 3),  # Tail Z+ X-
        (base + 1, base + 3, base + 5),  # Tail X- Z-
        (base + 1, base + 5, base + 2),  # Tail Z- X+
    ]

    return verts, faces

def processArmature(self, context, arm, genVertexGroups=True):
    self.report({'INFO'}, "Processing armature: {0}".format(arm.name))

    meshObj = meshFromArmature(arm)
    context.collection.objects.link(meshObj)

    verts = []
    edges = []
    faces = []
    vertexGroups = {}

    bpy.ops.object.mode_set(mode='EDIT')

    try:
        for editBone in [b for b in arm.data.edit_bones if b.use_deform]:
            boneName = editBone.name
            self.report({'DEBUG'}, f"Processing bone: {boneName}")

            editBoneHead = editBone.head
            editBoneTail = editBone.tail
            editBoneVector = editBoneTail - editBoneHead
            # editBoneSize = editBoneVector.dot(editBoneVector)
            editBoneX = editBone.x_axis
            editBoneZ = editBone.z_axis
            editBoneHeadRadius = editBone.head_radius
            editBoneTailRadius = editBone.tail_radius

            baseIndex = len(verts)
            # baseSize = sqrt(editBoneSize)
            baseSize = editBoneVector.length
            newVerts, newFaces = boneGeometry(editBoneHead, editBoneTail, editBoneX, editBoneZ, baseSize, editBoneHeadRadius, editBoneTailRadius, baseIndex, editBone.roll)

            verts.extend(newVerts)
            faces.extend(newFaces)

            # Weight paint the vertices to the bone
            vertexGroups[boneName] = [(x, 1.0) for x in range(baseIndex, len(verts))]

        meshObj.data.from_pydata(verts, edges, faces)

    except Exception as e:
        self.report({'ERROR'}, f"Error processing armature: {str(e)}")
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        bpy.ops.object.mode_set(mode='OBJECT')

    if genVertexGroups:
        for name, vertexGroup in vertexGroups.items():
            groupObject = meshObj.vertex_groups.new(name=name)
            for (index, weight) in vertexGroup:
                groupObject.add([index], weight, 'REPLACE')

    modifier = meshObj.modifiers.new('ArmatureMod', 'ARMATURE')
    modifier.object = arm
    modifier.use_bone_envelopes = False
    modifier.use_vertex_groups = True

    meshObj.data.update()

    return meshObj

class BoneToMeshOperator(bpy.types.Operator):
    bl_idname = "object.bone_to_mesh"
    bl_label = "Create Mesh from Bones"
    bl_description = "Create a mesh from the selected bone"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if createMesh(self, context):
            return {'FINISHED'}
        return {'CANCELLED'}

def register():
    bpy.utils.register_class(VIEW3D_PT_BoneToMeshPanel)
    bpy.utils.register_class(BoneToMeshOperator)
    

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_BoneToMeshPanel)
    bpy.utils.unregister_class(BoneToMeshOperator)

if __name__ == "__main__":
    register()