import struct, re, os, sys, io

from ctypes import *
from bsp2obj.helpers import *
from bsp2obj.constants import *

class PAKCollection(object):
    def __init__(self, game, paths):
        self.game = game
        self.list = []

        for path in paths:
            path = os.path.join(sys.path[0], path)
            with open(path, "rb") as f:
                data = io.BytesIO(f.read())
                pak = PAK(game, data)
                self.list.append(pak)

    # Look for the given object in our PAK collection and,
    # failing that lookup, check the filesystem
    def dataForEntry(self, name):
        pak, entry = self.entryForName(name)
        if pak is not None:
            pak.data.seek(entry.offset)
            size = entry.compressedSize if entry.isCompressed else entry.size
            data = pak.data.read(size)

            if entry.isCompressed:
                return self.decompressData(data)

            return io.BytesIO(data)
        else:
            try:
                with open(name, "rb") as f:
                    return io.BytesIO(f.read())
            except:
                return None

        return None

    # Based on https://gist.github.com/DanielGibson/a53c74b10ddd0a1f3d6ab42909d5b7e1
    def decompressData(self, input):
        input = io.BytesIO(input)
        output = io.BytesIO()
        endian = 'big'

        while input.tell() < len(input.getbuffer()):
            x = int.from_bytes(input.read(1), endian)
            if x < 64:
                output.write(input.read(x+1))
            elif x < 128: # run-length encoded zeroes
                for p in range(0, x-62):
                    output.write(b'\x00')
            elif x < 192:
                byte = input.read(1)
                for p in range(0, x-126):
                    output.write(byte)
            elif x < 254:
                offset = int.from_bytes(input.read(1), endian)
                prevOffset = output.tell()
                output.seek(prevOffset - (offset+2))
                uncompressedData = output.read(x-190)
                output.seek(prevOffset)
                output.write(uncompressedData)
            elif x == 255:
                break

        output.seek(0)
        return output

    def dumpContents(self, pattern):
        for pak in self.list:
            pak.dumpContents(pattern)

    def entryForName(self, name):
        for pak in self.list:
            if name in pak.directory:
                return pak, pak.directory[name]

        return None, None

class PAKEntry(object):
    def __init__(self, offset, size, compressedSize=0, isCompressed=False):
        self.offset = offset
        self.size = size
        self.compressedSize = compressedSize
        self.isCompressed = isCompressed

class PAK(object):
    def __init__(self, game, data):
        self.game = game
        self.data = data

        header, = struct.unpack("4s", data.read(4))
        header = bytesToString(header)

        if(header != "PACK"):
            raise ValueError("Expected PACK header, found " + header)
            
        # Get the offset and size of the PAK directory list
        offset, size = struct.unpack('ii', data.read(8))
        data.seek(offset)

        FILE_INDEX_SIZE_BYTES = 64
        if game is Game.DAIKATANA:
            FILE_INDEX_SIZE_BYTES = 72

        self.directory = {}
        for i in range(0, size // FILE_INDEX_SIZE_BYTES):
            if game is Game.DAIKATANA:
                filename, offset, size, compressedSize, isCompressed = struct.unpack("56siiii", data.read(FILE_INDEX_SIZE_BYTES))
                filename = c_char_p(filename).value # null-terminate string
                filename = bytesToString(filename)
                self.directory[filename] = PAKEntry(offset, size, compressedSize, isCompressed)
            else:
                filename, offset, size = struct.unpack("56sii", data.read(FILE_INDEX_SIZE_BYTES))
                filename = c_char_p(filename).value # null-terminate string
                filename = bytesToString(filename)
                self.directory[filename] = PAKEntry(offset, size, 0, False)

    def dumpContents(self, pattern):
        print("Dumping PAK contents matching `%s`"%(pattern))
        for filename in self.directory:
            if pattern is "*" or re.search(pattern, filename):
                print(filename)

