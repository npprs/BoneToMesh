import bpy
import mathutils
from mathutils import Vector
import math
from math import sqrt

def CreateMesh():
    obj = bpy.context.active_object

    if obj is None:
        print("No selection")
    elif obj.type != 'ARMATURE':
        print("Armature expected")
    else:
        processArmature(bpy.context, obj)

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

def processArmature(context, arm, genVertexGroups=True):
    print("processing armature {0}".format(arm.name))

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
            print(boneName)

            editBoneHead = editBone.head
            editBoneTail = editBone.tail
            editBoneVector = editBoneTail - editBoneHead
            editBoneSize = editBoneVector.dot(editBoneVector)
            editBoneX = editBone.x_axis
            editBoneZ = editBone.z_axis
            editBoneHeadRadius = editBone.head_radius
            editBoneTailRadius = editBone.tail_radius

            baseIndex = len(verts)
            baseSize = sqrt(editBoneSize)
            newVerts, newFaces = boneGeometry(editBoneHead, editBoneTail, editBoneX, editBoneZ, baseSize, editBoneHeadRadius, editBoneTailRadius, baseIndex, editBone.roll)

            verts.extend(newVerts)
            faces.extend(newFaces)

            # Weight paint the vertices to the bone
            vertexGroups[boneName] = [(x, 1.0) for x in range(baseIndex, len(verts))]

        meshObj.data.from_pydata(verts, edges, faces)

    except Exception as e:
        print(f"Error processing armature: {e}")
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

class MeshFromArmatureOperator(bpy.types.Operator):
    bl_idname = "object.mesh_from_armature"
    bl_label = "Mesh From Armature"

    def execute(self, context):
        CreateMesh()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(MeshFromArmatureOperator)

def unregister():
    bpy.utils.unregister_class(MeshFromArmatureOperator)

if __name__ == "__main__":
    register()