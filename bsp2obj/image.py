import io, struct, os, sys

from bsp2obj.constants import * 
from bsp2obj.helpers import * 
from PIL import Image
from ctypes import *

""" Handles loading images in various obscure formats from byte buffers """
class TextureLoader(object):
    @staticmethod
    def fromByteBuffer(data):
        img = Image.open(data).convert("RGB")
        width, height = img.size
        return Texture(list(img.getdata()), width, height, "")

    @staticmethod
    def fromLMP(data):
        buffer = data.getbuffer()

        pixels = []
        for i in range(0, len(buffer), 3):
            r, g, b = struct.unpack("BBB", buffer[i+0:i+3])
            pixels.append((r, g, b))
            
        return Texture(pixels, 0, 0, "")

    @staticmethod
    def loadFromPath(path, paks):
        data = None

        data = paks.dataForEntry(path)
        if data is None:
            return None

        if path.endswith(".lmp"):
            texture = TextureLoader.fromLMP(data)
            texture.name = path
            return texture
        else:
            texture = TextureLoader.fromByteBuffer(data)
            texture.name = path
            return texture

    @staticmethod
    def loadWAL(format, data, palette):
        baseOffset = data.tell()

        if format is BSPFormat.IBSP:
            byteFormat = "32sIIIIII"
            byteLength = 56
        else:
            byteLength = 40
            byteFormat = "16sIIIIII"

        # Parse texture header
        name, width, height, offset1, offset2, offset4, offset8 = struct.unpack(byteFormat, data.read(byteLength))
        name = c_char_p(name).value # null-terminate string
        name = bytesToString(name)

        # TODO: Apparently in Half-Life 1 the mip texture offsets can be 0
        # to denote that this texture should be loaded from an external WAD
        # file, but I've yet to come across this

        # Half-Life 1 stored custom palette information for each mip texture,
        # so we seek past the last mip texture (and past the 256 2-byte denominator)
        # to grab the RGB values for this texture
        if format is BSPFormat.HL:
            data.seek(baseOffset + offset8 + ((width//8) * (height//8)) + 2)
            palette = TextureLoader.fromLMP(io.BytesIO(data.read(256*3)))

        # Skip to the correct byte offset for mip level 1
        data.seek(baseOffset + offset1)

        # Grab the raw pixel data
        numPixels = width * height
        pixels = []
        for p in range(0, numPixels):
            index, = struct.unpack("B", data.read(1))
            if index >= len(palette.pixels):
                raise KeyError("Color index %i larger than palette size of %i"%(index, len(palette.pixels)))
                
            pixels.append(palette.pixels[index])

        return Texture(pixels, width, height, name)

class Texture(object):
    def __init__(self, pixels, width, height, name=None):
        self.pixels = pixels 
        self.width = width 
        self.height = height
        self.name = name

    def save(self, path):
        # Because texture names (and by extension the paths we write to)
        # can contain directories, i.e: 'e1u1/flat1_1' in the case of Quake 2,
        # we need to make sure the directories in the path are recursively created before writing
        folderPath = os.path.dirname(path)
        if len(folderPath) > 0:
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

        img = Image.new("RGB", (self.width, self.height))
        img.putdata(self.pixels)
        img.save(path)
