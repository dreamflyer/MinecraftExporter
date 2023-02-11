import bpy
import bmesh
import numpy as np

print("Starting export to Minecraft...");

selected = bpy.context.selected_objects[0]

bm = None

def toMinecraftCoords(position):
    return Position(position.x, -position.z, position.y)

def toBlenderCoords(position):
    return Position(position.x, position.z, -position.y)
 
class Size:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    
    def toJSON(self):
        return '{"x":' + format(self.x, ".20f") + ',"y":' + format(self.y, ".20f") + ',"z":' + format(self.z, ".20f") + "}"

class Position:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    
    def toJSON(self):
        return '{"x":' + format(self.x, ".20f") + ',"y":' + format(self.y, ".20f") + ',"z":' + format(self.z, ".20f") + "}"

class Position2d:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def toJSON(self):
        return '{"x":' + format(self.x, ".20f") + ',"y":' + format(self.y, ".20f") + "}"

class UVMap:
    def __init__(self, offset, size):
        self.offset = offset
        self.size = size
    
    def toJSON(self):
        result = "{"
        result += '"offset":' + self.offset.toJSON() + ','
        result += '"size":' + self.size.toJSON()
        result += "}"
        
        return result;

class Cube:
    def __init__(self, start, end, mapper):
        self.start = start
        self.end = end
        self.mapper = mapper
        self.uvMap = UVMap(Position2d(0, 0), Size(1, 1, 1))
    
    def toJSON(self):
        result = "{"
        result += '"start":' + self.start.toJSON() + ','
        result += '"end":' + self.end.toJSON() + ','
        result += '"uvMap":' + self.uvMap.toJSON()
        result += "}"
        
        return result;
    
    def applySize(self):
        bStart = toBlenderCoords(self.start)
        bEnd = toBlenderCoords(self.end)
        
        self.mapper.apply(Size(bEnd.x - bStart.x, bStart.z - bEnd.z, bEnd.y - bStart.y))
    
    def sync(self):
        self.uvMap = UVMap(self.mapper.getOffset(), self.mapper.getSize())

class ModelNode:
    def __init__(self, selected, bone):
        self.bone = bone
        self.name = bone.name
        
        parentPos = Position(bone.parent.head_local[0], bone.parent.head_local[1], bone.parent.head_local[2]) if bone.parent else Position(0, 0, 0)
        
        selfPos = Position(bone.head_local[0], bone.head_local[1], bone.head_local[2])
        
        self.mountPoint = toMinecraftCoords(Position(selfPos.x - parentPos.x, selfPos.y - parentPos.y, selfPos.z - parentPos.z))
        
        self.children = []
        
        self.mesh = cubesForBone(selected, bone)
    
    def add(self, node):
        self.children.append(node)
        
    def toJSON(self):
        result = "{"
        result += '"name":"' + self.name + '",'
        result += '"mountPoint":' + self.mountPoint.toJSON() + ','
        result += '"mesh":[' + ",".join([item.toJSON() for item in self.mesh]) + '],'
        result += '"children":[' + ",".join([item.toJSON() for item in self.children]) + ']'
        result += "}";
        
        return result

class BlenderUvMapper:
    def __init__(self, selected, polygons, distributedCloud):
        self.TOP_FACE_NUMBERS = (2, 3, 7, 6)
        self.FRONT_FACE_NUMBERS = (0, 2, 6, 4)
        self.LEFT_FACE_NUMBERS = (1, 3, 2, 0)
        self.RIGHT_FACE_NUMBERS = (4, 6, 7, 5)
        self.BOTTOM_FACE_NUMBERS = (1, 0, 4, 5)
        self.BACK_FACE_NUMBERS = (5, 7, 3, 1)
        
        self.selected = selected
        
        self.polygons = polygons
        
        self.distributedCloud = distributedCloud
        
        self.uvs = [item for item in selected.data.uv_layers.active.data]
        
        self.numbers = [self.TOP_FACE_NUMBERS, self.FRONT_FACE_NUMBERS, self.LEFT_FACE_NUMBERS, self.RIGHT_FACE_NUMBERS, self.BOTTOM_FACE_NUMBERS, self.BACK_FACE_NUMBERS]
    
    def update(self, selected, uvs):
        self.selected = selected
        self.uvs = uvs
    
    def _apply(self, w, h, d):
        top_face = [(d, h), (d,  h + d), (d + w, h + d), (d + w, h)]
        front_face = [(d, 0), (d, h), (d + w, h), (d + w, 0)]
        left_face = [(0, 0), (0, h), (d, h), (d, 0)]
        right_face = [(d + w, 0), (d + w, h), (2.0 * d + w, h), (2.0 * d + w, 0)]
        bottom_face = [(d + w, d + h), (d + w, h), (d + 2.0 * w, h), (d + 2.0 * w, d + h)]
        back_face = [(2.0 * d + w, 0), (2.0 * d + w, h), (2.0 * d + 2.0 * w, h), (2.0 * d + 2.0 * w, 0)]
        
        for i, item in enumerate([top_face, front_face, left_face, right_face, bottom_face, back_face]):
            self.applyForPolygon(item, self.numbers[i])
    
    def loopIndex(self, polygon, number):
        vertexId = self.distributedCloud[number]
        
        for item in polygon.loop_indices:
            if selected.data.loops[item].vertex_index == vertexId:
                return item
        
        return None
    
    def getOffset(self):
        topUvs = self.numbersToUvs(self.TOP_FACE_NUMBERS)
        leftUvs = self.numbersToUvs(self.LEFT_FACE_NUMBERS)
        
        return Position2d(leftUvs[1].uv[0], 1 - topUvs[1].uv[1])
    
    def getSize(self):
        topUvs = self.numbersToUvs(self.TOP_FACE_NUMBERS)
        frontUvs = self.numbersToUvs(self.FRONT_FACE_NUMBERS)
        
        width = frontUvs[2].uv[0] - frontUvs[1].uv[0]
        height = frontUvs[1].uv[1] - frontUvs[0].uv[1]
        depth = topUvs[1].uv[1] - topUvs[0].uv[1]
        
        return Size(width, height, depth)
    
    def numbersToLoopIndeces(self, numbers):
        polygon = self.findPolygon(numbers)
        
        return [self.loopIndex(polygon, item) for item in numbers]
    
    def numbersToUvs(self, numbers):
        loopIndices = self.numbersToLoopIndeces(numbers)
        
        return [self.uvs[item] for item in loopIndices]
    
    def hideBottom(self):
        polygon = self.findPolygon(self.BOTTOM_FACE_NUMBERS)
        
        bm.faces[polygon.index].select_set(False)
    
    def restoreBottom(self):
        topUvs = self.numbersToUvs(self.TOP_FACE_NUMBERS)
        bottomUvs = self.numbersToUvs(self.BOTTOM_FACE_NUMBERS)
        
        width = topUvs[3].uv[0] - topUvs[0].uv[0]
        
        bottomUvs[0].uv = (topUvs[2].uv[0], topUvs[2].uv[1])
        bottomUvs[1].uv = (topUvs[3].uv[0], topUvs[3].uv[1])
        bottomUvs[2].uv = (topUvs[3].uv[0] + width, topUvs[3].uv[1])
        bottomUvs[3].uv = (topUvs[2].uv[0] + width, topUvs[2].uv[1])
    
    def findPolygon(self, faceNumbers):
        vertices = [self.distributedCloud[item] for item in faceNumbers]
        
        for item in self.polygons:
            matches = [item1 for item1 in vertices if (item1 in item.vertices)]
            
            if len(matches) == 4:
                return item
        
        return None
        
    def apply(self, size):
        self._apply(size.x, size.y, size.z)
        
    def applyForPolygon(self, toApply, numbers):
        uvs = self.numbersToUvs(numbers)
        
        for i, item in enumerate(uvs):
            item.uv = toApply[i]

def contains(item, list):
    for item1 in list:
        if item1 == item:
            return True
    
    return False

def hasIntersection(list1, list2):
    for v1 in list1:
        for v2 in list2:
            if v1 == v2:
                return True
    
    return False

def addToCloud(vertices, cloud):
    for item in vertices:
        if(not contains(item, cloud)):
            cloud.append(item)

def getNeighbour(vertexId, edge):
    if(vertexId == edge.vertices[0]):
        return edge.vertices[1]
    
    return edge.vertices[0]

def getNeighbours(selected, vertexId, excludedVertices):
    neighbours = [getNeighbour(vertexId, edge) for edge in selected.data.edges if ((edge.vertices[0] == vertexId) or (edge.vertices[1] == vertexId))]
    
    return set([item for item in neighbours if not (item in excludedVertices)])

def collectConnectedForVertexId(selected, vertexId):
    result = set([])
    
    result.add(vertexId);
    
    neighbours = getNeighbours(selected, vertexId, result)
    
    while neighbours:
        [result.add(item) for item in neighbours]
        
        for item in result:
            neighbours = getNeighbours(selected, item, result)
            
            if(neighbours):
                break
    
    return result

def connectedVertices(selected, _vertices):
    ids = set([item.index for item in _vertices])
    
    result = []
    
    while ids:
        connected = collectConnectedForVertexId(selected, ids.pop())
        
        [ids.remove(item) for item in connected if item in ids]
        
        if connected:
            result.append(connected)
    
    return result

def assignedToGroup(vertex, groupIndex):
    return len([item for item in vertex.groups if ((item.group == groupIndex) and (item.weight > 0.5))]) > 0

def verticesForBone(selected, bone):
    name = bone.name
    
    groups = [item for item in selected.vertex_groups if item.name == name]
    
    if(len(groups) == 0):
        return []
    
    return [v for v in selected.data.vertices if assignedToGroup(v, groups[0].index)]

def getArmature(selectedObject):
    return [item for item in selectedObject.modifiers if item.name == "Armature"][0].object

def rootBone(armature):
    for item in armature.data.bones:
        if(len(item.parent_recursive) == 0):
            return item

def cloudOfIdsToCloudOfVerices(selected, cloudOfIds):
    return [selected.data.vertices[item] for item in cloudOfIds]

def getMin(current, test):
    if test < current:
        return test
    
    return current

def getMax(current, test):
    if test > current:
        return test
    
    return current

def distribute(selected, cloudOfVertices):
    coords = np.array([item.undeformed_co for item in cloudOfVertices], np.float32)
    
    middle = np.average(coords, 0)
    
    directions = (np.sign(coords - middle) + 1) / 2.0
    
    ids = [item for item in (directions[:, 0] * 4 + directions[:, 2] * 2 + directions[:, 1]).astype(np.int32)]
    
    result = [0, 0, 0, 0, 0, 0, 0, 0];
    
    for i, item in enumerate(ids):
        result[item] = cloudOfVertices[i]
    
    return result

def getUvMapper(selected, cloudOfVertices):
    distributedCloud = distribute(selected, cloudOfVertices)
    
    cloudOfIds = [item.index for item in cloudOfVertices]
    
    polygons = [item for item in selected.data.polygons if item.vertices[0] in cloudOfIds]
    
    return BlenderUvMapper(selected, polygons, [item.index for item in distributedCloud])
    
def cloudToMinecraftCloud(selected, bone, cloudOfVerts):
    coordinates = [item.undeformed_co for item in cloudOfVerts]
    
    return [toMinecraftCoords(Position(item[0] - bone.head_local[0], item[1] - bone.head_local[1], item[2] - bone.head_local[2])) for item in coordinates]

def cloudToCube(selected, bone, cloudOfIds):
    cloudOfVertices = cloudOfIdsToCloudOfVerices(selected, cloudOfIds)
    
    positions = cloudToMinecraftCloud(selected, bone, cloudOfVertices)
    
    mapper = getUvMapper(selected, cloudOfVertices)
    
    lx = float('+inf');
    ly = float('+inf');
    lz = float('+inf');
    
    rx = float('-inf');
    ry = float('-inf');
    rz = float('-inf');
    
    for item in positions:
        lx = getMin(lx, item.x);
        ly = getMin(ly, item.y);
        lz = getMin(lz, item.z);
        
        rx = getMax(rx, item.x);
        ry = getMax(ry, item.y);
        rz = getMax(rz, item.z);
    
    return Cube(Position(lx, ly, lz), Position(rx, ry, rz), mapper)

def cubesForBone(selected, bone):
    verts = verticesForBone(selected, bone)
    
    connected = connectedVertices(selected, verts)
    
    return [cloudToCube(selected, bone, item) for item in connected]

def buildMincraftModel(selected, parentBone):
    node = ModelNode(selected, parentBone);
    
    for item in parentBone.children:
        node.add(buildMincraftModel(selected, item))
    
    return node

def applySizes(model):
    for item in model.mesh:
        item.applySize()
    
    for item in model.children:
        applySizes(item)

def hideBottoms(model):
    for item in model.mesh:
        item.mapper.hideBottom()
        #item.applySize()
    
    for item in model.children:
        hideBottoms(item)

def restoreBottoms(model, selected, uvs):
    for item in model.mesh:
        item.mapper.update(selected, uvs)
        
        item.mapper.restoreBottom()
    
    for item in model.children:
        restoreBottoms(item, selected, uvs)

def syncUvs(model):
    for item in model.mesh:
        item.sync()
    
    for item in model.children:
        syncUvs(item)

model = buildMincraftModel(selected, rootBone(getArmature(selected)))

applySizes(model)

bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_mode(type="VERT")
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')

bm = bmesh.from_edit_mesh(selected.data)

bm.faces.ensure_lookup_table()
bm.verts.ensure_lookup_table()

bm.select_mode = {'FACE'}

bottoms = hideBottoms(model)

bm.select_flush(False)
bm.select_flush_mode()

bmesh.update_edit_mesh(selected.data, True)

bm.free()

bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=False, margin=0.001)

bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')

bpy.ops.object.mode_set(mode="OBJECT")

selected = bpy.context.selected_objects[0]

uvs = [item for item in selected.data.uv_layers.active.data]

restoreBottoms(model, selected, uvs)

syncUvs(model)

print(model.toJSON())