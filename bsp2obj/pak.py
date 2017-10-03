import struct
from ctypes import *

class PAK(object):
    def __init__(self, stream):
        self.stream = stream

        header, = struct.unpack("4s", stream.read(4))
        if(header != "PACK"):
            raise ValueError("Expected PACK header, found " + header)
            
        # Get the offset and size of the PAK directory list
        offset, size = struct.unpack('ii', stream.read(8))
        stream.seek(offset)

        FILE_INDEX_SIZE_BYTES = 64
        self.directory = {}
        for i in range(0, size / FILE_INDEX_SIZE_BYTES):
            filename, offset, size = struct.unpack("56sii", stream.read(FILE_INDEX_SIZE_BYTES))
            filename = c_char_p(filename).value # null-terminate string

            self.directory[filename] = (offset, size)
