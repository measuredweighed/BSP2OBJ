import math, struct

""" A barebones class to help with seeking and fetching from a binary source """
class BinaryStream(object):
    ptr = 0
    binaryFile = None

    def __init__(self, binaryFile, ptr=0):
        self.binaryFile = binaryFile
        self.ptr = ptr
        self.binaryFile.seek(ptr)

    def seek(self, ptr):
        self.binaryFile.seek(ptr)
        self.ptr = ptr

    def advance(self, length):
        self.seek(self.ptr+length)

    def rewind(self, length):
        self.advance(-length)

    def read(self, length):
        value = self.binaryFile.read(length)
        self.advance(length)
        return value

    def int(self, length):
        data = self.binaryFile.read(length)
        value, = struct.unpack("i", data)
        self.advance(length)
        return value

    def str(self, length, encoding=None):
        # default to ASCII encoding but make it possible to specify others
        if encoding is None:
            encoding = "ascii"

        value = self.binaryFile.read(length).decode(encoding)
        self.advance(length)
        return value

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
