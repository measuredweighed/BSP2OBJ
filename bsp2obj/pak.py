import struct, re, os, sys, io

from ctypes import *
from bsp2obj.helpers import *

class PAKCollection(object):
    def __init__(self, paths):
        self.list = []

        for path in paths:
            path = os.path.join(sys.path[0], path)
            with open(path, "rb") as f:
                data = io.BytesIO(f.read())
                pak = PAK(data)
                self.list.append(pak)

    # Look for the given object in our PAK collection and,
    # failing that lookup, check the filesystem
    def dataForEntry(self, name):
        pak, entry = self.entryForName(name)
        if pak is not None:
            offset, size = entry
            pak.data.seek(offset)
            data = pak.data.read(size)
            return io.BytesIO(data)
        else:
            try:
                with open(name, "rb") as f:
                    return io.BytesIO(f.read())
            except:
                return None

        return None

    def dumpContents(self, pattern):
        for pak in self.list:
            pak.dumpContents(pattern)

    def entryForName(self, name):
        for pak in self.list:
            if name in pak.directory:
                return pak, pak.directory[name]

        return None, None

class PAK(object):
    def __init__(self, data):
        self.data = data

        header, = struct.unpack("4s", data.read(4))
        header = bytesToString(header)

        if(header != "PACK"):
            raise ValueError("Expected PACK header, found " + header)
            
        # Get the offset and size of the PAK directory list
        offset, size = struct.unpack('ii', data.read(8))
        data.seek(offset)

        structure = "56sii" #56siiii" 

        FILE_INDEX_SIZE_BYTES = 64 #72
        self.directory = {}
        for i in range(0, size // FILE_INDEX_SIZE_BYTES):
            filename, offset, size = struct.unpack(structure, data.read(FILE_INDEX_SIZE_BYTES))
            filename = c_char_p(filename).value # null-terminate string
            filename = bytesToString(filename)

            self.directory[filename] = (offset, size)

    def dumpContents(self, pattern):
        print("Dumping PAK contents matching `%s`"%(pattern))
        for filename in self.directory:
            if pattern is "*" or re.search(pattern, filename):
                print(filename)

