import struct, re, os, sys

from ctypes import *
from bsp2obj.helpers import *

class PAKCollection(object):
    def __init__(self, paths):
        self.list = []

        for path in paths:
            try:
                path = os.path.join(sys.path[0], path)
                f = open(path, "rb")
                stream = BinaryStream(f)

                pak = PAK(stream)
                self.list.append(pak)
            except:
                raise ValueError("Failed to load PAK with path `%s`"%(path))

    def dumpContents(self, pattern):
        for pak in self.list:
            pak.dumpContents(pattern)

    def entryForName(self, name):
        for pak in self.list:
            if name in pak.directory:
                return pak, pak.directory[name]

        return None, None

    def closeAll(self):
        for pak in self.list:
            pak.close()

class PAK(object):
    def __init__(self, stream):
        self.stream = stream

        header, = struct.unpack("4s", stream.read(4))
        header = bytesToString(header)

        if(header != "PACK"):
            raise ValueError("Expected PACK header, found " + header)
            
        # Get the offset and size of the PAK directory list
        offset, size = struct.unpack('ii', stream.read(8))
        stream.seek(offset)

        FILE_INDEX_SIZE_BYTES = 64
        self.directory = {}
        for i in range(0, size // FILE_INDEX_SIZE_BYTES):
            filename, offset, size = struct.unpack("56sii", stream.read(FILE_INDEX_SIZE_BYTES))
            filename = c_char_p(filename).value # null-terminate string
            filename = bytesToString(filename)

            self.directory[filename] = (offset, size)

    def dumpContents(self, pattern):
        print("Dumping PAK contents matching `%s`"%(pattern))
        for filename in self.directory:
            if pattern is "*" or re.search(pattern, filename):
                print(filename)

    def close(self):
        self.stream.close()

