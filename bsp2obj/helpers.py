import math, struct, os

""" Converts a byte string representation to a string type (where appropriate) """
def bytesToString(bytes, encoding="ascii"):
    if type(bytes) == type(b""):
        bytes = bytes.decode(encoding, errors="ignore")
    return bytes

def createFolderStructure(path):
    folderPath = os.path.dirname(path)
    outputPath = ""
    if len(folderPath) > 0:
        outputPath = folderPath + "/"
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
            
    return outputPath

""" A barebones Vector3 implementation """
class Vector3(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    @staticmethod
    def swizzle(x, y, z):
        return Vector3(x, z, -y)

    def __sub__(self, v):
        return Vector3(self.x - v.x, self.y - v.y, self.z - v.z)

    def __eq__(self, v):
        if isinstance(v, Vector3):
            return self.x == v.x and self.y == v.y and self.z == v.z

    def __ne__(self, v):
        result = self.__eq__(v)
        if result is NotImplemented:
            return result
        return not result

    def cross(self, v):
        return Vector3(self.y * v.z - self.z * v.y, self.z * v.x - self.x * v.z, self.x * v.y - self.y * v.x)

    def dot(self, v):
        return self.x * v.x + self.y * v.y + self.z * v.z

    def lenSq(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self):
        lengthSq = self.lenSq()
        lengthSqrt = math.sqrt(lengthSq)
        if lengthSqrt == 0 or lengthSqrt == 1:
            return self

        return Vector3(self.x / lengthSqrt, self.y / lengthSqrt, self.z / lengthSqrt)
