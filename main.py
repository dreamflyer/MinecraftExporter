import bpy
import bmesh

print("Starting export to Minecraft...");

selected = bpy.context.selected_objects[0]

def toMinecraftCoords(position):
    return Position(position.x, -position.z, position.y)
 
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
    def __init__(self, start, end, uvMap):
        self.start = start
        self.end = end
        self.uvMap = uvMap
        
    def toJSON(self):
        result = "{"
        result += '"start":' + self.start.toJSON() + ','
        result += '"end":' + self.end.toJSON() + ','
        result += '"uvMap":' + self.uvMap.toJSON()
        result += "}"
        
        return result;

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

def getNeighbour(vertex, edge):
    if(vertex.index == edge.vertices[0]):
        return edge.vertices[1]
    
    return edge.vertices[0]

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

def connectedVertices(selected, _vertices):
    vertices = [item for item in _vertices]
    
    result = [];
    
    while len(vertices) > 0:
        current = vertices.pop()
        
        connectedVertices = [getNeighbour(current, edge) for edge in selected.data.edges if ((edge.vertices[0] == current.index) or (edge.vertices[1] == current.index))]
        
        connectedVertices.append(current.index)
        
        found = False
        
        for cloud in result:
            if(hasIntersection(cloud, connectedVertices)):
                addToCloud(connectedVertices, cloud)
                
                found = True
                
                break
        
        if(not found):
            cloud = []
            
            addToCloud(connectedVertices, cloud)
            
            result.append(cloud)
    
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

def visit(selected, parentBone):
    node = ModelNode(selected, parentBone);
    
    for item in parentBone.children:
        node.add(visit(selected, item))
    
    return node

def rootBone(armature):
    for item in armature.data.bones:
        if(len(item.parent_recursive) == 0):
            return item

def cloudToMinecraftCloud(selected, bone, cloud):
    verts = [selected.data.vertices[item] for item in cloud]
    
    coordinates = [item.undeformed_co for item in verts]
    
    return [toMinecraftCoords(Position(item[0] - bone.head_local[0], item[1] - bone.head_local[1], item[2] - bone.head_local[2])) for item in coordinates]

def getMin(current, test):
    if test < current:
        return test
    
    return current

def getMax(current, test):
    if test > current:
        return test
    
    return current

def cloudToCube(selected, bone, cloud):
    positions = cloudToMinecraftCloud(selected, bone, cloud)
    
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
     
    return Cube(Position(lx, ly, lz), Position(rx, ry, rz), UVMap(Position2d(0, 0), Size(1, 1, 1)))

def cubesForBone(selected, bone):
    verts = verticesForBone(selected, bone)
    
    connected = connectedVertices(selected, verts)
    
    return [cloudToCube(selected, bone, item) for item in connected]

print(visit(selected, rootBone(getArmature(selected))).toJSON())
