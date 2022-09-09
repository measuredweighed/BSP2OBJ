import struct

import re
from ctypes import *
from bsp2obj.helpers import *

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

