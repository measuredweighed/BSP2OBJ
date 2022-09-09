import os, io, struct, math

from bsp2obj.helpers import *
from bsp2obj.pak import *

from enum import Enum
from PIL import Image

class Edge(object):
    def __init__(self, vert1, vert2):
        self.vert1 = vert1
        self.vert2 = vert2

class Face(object):
    def __init__(self, lEdgeIndex, numLEdges, texInfoID):
        self.lEdgeIndex = lEdgeIndex
        self.numLEdges = numLEdges
        self.texInfoID = texInfoID

class TextureInfo(object):
    def __init__(self, name, uAxis, uOffset, vAxis, vOffset, texID, animated):
        self.name = name # can be None for GoldSrc BSPs
        self.uAxis = uAxis
        self.uOffset = uOffset
        self.vAxis = vAxis 
        self.vOffset = vOffset
        self.texID = texID
        self.animated = animated

class Palette(object):
    @staticmethod
    def fromPCX(data):
        stream = io.BytesIO(data)
        img = Image.open(stream).convert("RGB")
        return list(img.getdata())

    @staticmethod
    def fromLMP(data):
        pixels = []
        for i in range(0, len(data), 3):
            r, g, b = struct.unpack('BBB', data[i+0:i+3])
            pixels.append((r, g, b))
        return pixels

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

    def saveToAtlas(self, atlas, position):
        img = Image.new("RGB", (self.width, self.height))
        img.paste(atlas, position)

class TextureGroup(object):
    def __init__(self, vertexIndices, uvIndices, normalIndices):
        self.vertexIndices = vertexIndices
        self.uvIndices = uvIndices
        self.normalIndices = normalIndices

class BSPFormat(Enum):
    GSRC = 1 # Quake
    IBSP = 2 # Quake 2 (also used for Quake 3, but that's unsupported right now)
    HL = 3 # Half-Life

class BSP(object):
    def __init__(self, stream, pak, palettePath):
        self.stream = stream
        self.pak = pak
        self.format = BSPFormat.GSRC

        # Store a base byte offset to the start of the BSP file
        offset = stream.ptr

        numLumps = 0

        identStr, = struct.unpack("4s", self.stream.read(4))
        if identStr == "IBSP":
            self.format = BSPFormat.IBSP
            numLumps = 19
        else:
            # GoldSrc-era BSP files don't have any ident value, so we assume this is Quake
            # In which case we need to rewind 4 bytes as we've just read the BSP version accidentally 
            self.stream.rewind(4)
            numLumps = 15

        version, = struct.unpack("I", self.stream.read(4))
        print("BSP version " + str(version))

        # Version 30 of the old GoldSrc format is Half-Life (AKA: HL)
        if self.format is BSPFormat.GSRC and version is 30:
            self.format = BSPFormat.HL

        self.palette = self.loadGlobalPalette(palettePath)

        # Parse this BSPs lumps
        lumps = []
        for i in range(0, numLumps):
            lump = struct.unpack("II", self.stream.read(8))
            lumps.append(lump)

        if self.format is BSPFormat.GSRC or self.format is BSPFormat.HL:
            self.textures = self.parseTextures(offset + lumps[2][0])
            self.vertices = self.parseVertices(offset + lumps[3][0], lumps[3][1])
            self.texInfos = self.parseTextureInfo(offset + lumps[6][0], lumps[6][1])
            self.faces = self.parseFaces(offset + lumps[7][0], lumps[7][1])
            self.edges = self.parseEdges(offset + lumps[12][0], lumps[12][1])
            self.lEdges = self.parseLEdges(offset + lumps[13][0], lumps[13][1])

        else:
            self.vertices = self.parseVertices(offset + lumps[2][0], lumps[2][1])
            self.texInfos = self.parseTextureInfo(offset + lumps[5][0], lumps[5][1])
            self.faces = self.parseFaces(offset + lumps[6][0], lumps[6][1])
            self.edges = self.parseEdges(offset + lumps[11][0], lumps[11][1])
            self.lEdges = self.parseLEdges(offset + lumps[12][0], lumps[12][1])

            self.textures = {}
            for texInfo in self.texInfos:
                if texInfo.name not in self.textures:
                    path = "textures/" + texInfo.name + ".wal"

                    if (self.pak is not None) and (path in self.pak.directory):
                        offset = self.pak.directory[path][0]
                        self.textures[texInfo.name] = self.parseTexture(BinaryStream(self.stream.binaryFile, offset))

    def loadGlobalPalette(self, path):
        ptr = self.stream.ptr

        if self.pak is not None:
            if path not in self.pak.directory:
                raise KeyError("Unable to find palette file `%s` in PAK file"%(path))

            offset, size = self.pak.directory[path]

            self.stream.seek(offset)
            data = self.stream.read(size)
            self.stream.seek(ptr)

            if path.endswith(".lmp"):
                return Palette.fromLMP(data)
            else:
                return Palette.fromPCX(data)
        else:
            with open(path, "rb") as f:
                stream = BinaryStream(f)
                size = os.fstat(f.fileno()).st_size
                data = self.stream.read(size)
                self.stream.seek(ptr)

                if path.endswith(".lmp"):
                    return Palette.fromLMP(data)
                else:
                    return Palette.fromPCX(data)

        return None

    def saveOBJ(self, outputFileName):
        faceIndices = []
        uvs = []
        uvIndices = []
        normals = []

        textureGroups = {}
        for face in self.faces:
            texInfo = self.texInfos[face.texInfoID]
            texture = self.textures[texInfo.name if texInfo.name is not None else texInfo.texID]

            # Ignore trigger volumes as they're invisible
            if texture.name.endswith("trigger"):
                continue

            # If this is the first piece of geometry using this texture make
            # a new texture group for it
            if texture.name not in textureGroups:
                textureGroups[texture.name] = TextureGroup([], [], [])

            vertexIndices = []
            e = face.lEdgeIndex
            uvOffset = len(uvs)

            # Since we've already got a master list of vertices we need to iterate over our
            # edge list and generate vertex indices. We'll also generate UV coordinates for
            # each vertex as we go...
            for i in range(0, face.numLEdges):
                if(self.lEdges[face.lEdgeIndex + i] < 0):
                    vertexIndices.append(self.edges[abs(self.lEdges[e])].vert1)
                else:
                    vertexIndices.append(self.edges[self.lEdges[e]].vert2)

                # calculate UV coordinates
                vertex = self.vertices[vertexIndices[i]]
                u = (vertex.dot(texInfo.uAxis) + texInfo.uOffset) / texture.width
                v = (vertex.dot(texInfo.vAxis) + texInfo.vOffset) / texture.height
                uvs.append((u, 1-v))

                e += 1

            # Next we iterate over all of our vertex indices and generate triangular faces.
            # At the same time, we generate one normal per-face. 
            # TODO: there's a ton of normal duplication, we should index them
            for i in range(1, len(vertexIndices)-1):
                vA = self.vertices[vertexIndices[0]]
                vB = self.vertices[vertexIndices[i]]
                vC = self.vertices[vertexIndices[i+1]]

                # Generate a normal for the triangular face
                U = vB - vA
                V = vC - vA
                normal = U.cross(V).normalized()
                normals.append(normal)

                textureGroups[texture.name].vertexIndices.append((vertexIndices[i+1], vertexIndices[i], vertexIndices[0]))
                textureGroups[texture.name].uvIndices.append((uvOffset+i+1, uvOffset+i, uvOffset+0))
                textureGroups[texture.name].normalIndices.append(len(normals))

        # Generate any required folders for the output path
        folderPath = os.path.dirname(outputFileName)
        outputPath = ""
        if len(folderPath) > 0:
            outputPath = folderPath + "/"
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

        outputPath += outputFileName

        # Generate an OBJ file for this map
        with open(outputPath + ".obj", "w") as outputFile:
            outputFile.write("mtllib " + outputFileName + ".mtl\n\n")

            for vertex in self.vertices:
                outputFile.write("v " + str(vertex.x) + " " + str(vertex.y) + " " + str(vertex.z) + "\n")

            for normal in normals:
                outputFile.write("v " + str(normal.x) + " " + str(normal.y) + " " + str(normal.z) + "\n")

            for uv in uvs:
                outputFile.write("vt " + str(uv[0]) + " " + str(uv[1]) + "\n")

            numFaces = len(faceIndices)
            for name, group in textureGroups.items():
                outputFile.write("\no mesh_" + name + "\n")
                outputFile.write("\nusemtl " + name + "\n")

                for i in range(0, len(group.vertexIndices)):
                    fA = group.vertexIndices[i][0]+1
                    fB = group.vertexIndices[i][1]+1
                    fC = group.vertexIndices[i][2]+1

                    uvA = group.uvIndices[i][0]+1
                    uvB = group.uvIndices[i][1]+1
                    uvC = group.uvIndices[i][2]+1

                    # All vertices in a face share a normal (flat shading)
                    n = group.normalIndices[i]

                    line = "f " + str(fA) + "/" + str(uvA) + "/" + str(n) + " " + str(fB) + "/" + str(uvB) + "/" + str(n) + " " + str(fC) + "/" + str(uvC) + "/" + str(n) + "\n"
                    outputFile.write(line)

        # Generate the MTL file to go alongside our OBJ
        with open(outputPath + ".mtl", "w") as mtlFile:
            for name, group in textureGroups.items():
                mtlFile.write("\nnewmtl " + name + "\n")
                mtlFile.write("Ka 1.000 1.000 1.000\n")
                mtlFile.write("Kd 1.000 1.000 1.000\n")
                mtlFile.write("Ks 0.000 0.000 0.000\n")
                mtlFile.write("d 1.0\n")
                mtlFile.write("illum 2\n")
                mtlFile.write("map_Ka " + outputFileName + "/" + name + ".png\n")
                mtlFile.write("map_Kd " + outputFileName + "/" + name + ".png\n")

            mtlFile.close()

        # We treat the texture list a little differently for GoldSrc versus later BSP versions.
        if self.format is not BSPFormat.IBSP:
            for texture in self.textures:
                texture.save(outputFileName + "/" + texture.name + ".png")
        else:
            textureList = self.textures.values()
            for texture in textureList:
                texture.save(outputFileName + "/" + texture.name + ".png")

    def parseVertices(self, offset, size):
        self.stream.seek(offset)

        vertices = []
        for i in range(0, size//12):
            vertex = struct.unpack("fff", self.stream.read(12))
            vertices.append(Vector3.swizzle(vertex[0], vertex[1], vertex[2]))

        return vertices

    def parseLEdges(self, offset, size):
        self.stream.seek(offset)

        edgeList = []
        for i in range(0, size//4):
            index, = struct.unpack("i", self.stream.read(4))
            edgeList.append(index)

        return edgeList

    def parseEdges(self, offset, size):
        self.stream.seek(offset)

        edges = []
        for i in range(0, size//4):
            data = struct.unpack("HH", self.stream.read(4))
            edges.append(Edge(data[0], data[1]))
    
        return edges

    def parseFaces(self, offset, size):
        self.stream.seek(offset)

        faces = []
        for i in range(0, size//20):
            self.stream.advance(4) # skip plane index

            data = struct.unpack("ihh", self.stream.read(8))
            faces.append(Face(data[0], data[1], data[2]))

            self.stream.advance(8) # skip lightmap info
        
        return faces

    def parseTextureInfo(self, offset, size):
        self.stream.seek(offset)

        length = 40
        if self.format is BSPFormat.IBSP:
            length = 76

        print(length)

        texInfos = []
        for i in range(0, size//length):
            name = None

            # GoldSrc BSP files didn't contain texture names as part of the texInfo lump
            # because all textures were contained within the BSP file itself. When future
            # versions of the engine made it possible to store texture data outside of BSP files
            # it became necessary to pack texInfo with texture names for external look-up
            if self.format is BSPFormat.IBSP:
                data = struct.unpack("ffffffffII32sI", self.stream.read(length))
                name = c_char_p(data[10]).value
            else:
                data = struct.unpack("ffffffffII", self.stream.read(length))

            uAxis = Vector3.swizzle(data[0], data[1], data[2])
            uOffset = data[3]
            vAxis = Vector3.swizzle(data[4], data[5], data[6])
            vOffset = data[7]
            textureID = data[8]
            animated = data[9]

            texInfos.append(TextureInfo(name, uAxis, uOffset, vAxis, vOffset, textureID, animated))

        return texInfos

    def parseTextures(self, offset):
        if self.palette == None:
            raise ValueError("Attempt to parse a texture without an associated palette")

        self.stream.seek(offset)

        numTextures, = struct.unpack("I", self.stream.read(4))
        offsets = []

        for i in range (0, numTextures):
            textureOffset, = struct.unpack("I", self.stream.read(4))
            offsets.append(textureOffset)

        textures = []
        for i in range(0, numTextures):
            textureStream = BinaryStream(self.stream.binaryFile, offset + offsets[i])
            textures.append(self.parseTexture(textureStream))

        return textures

    def parseTexture(self, stream):
        baseOffset = stream.ptr

        if self.format is BSPFormat.IBSP:
            byteFormat = "32sIIIIII"
            byteLength = 56
        else:
            byteLength = 40
            byteFormat = "16sIIIIII"

        # Parse texture header
        name, width, height, offset1, offset2, offset4, offset8 = struct.unpack(byteFormat, stream.read(byteLength))
        name = c_char_p(name).value # null-terminate string
        name = bytesToString(name)

        # TODO: Apparently in Half-Life 1 the mip texture offsets can be 0
        # to denote that this texture should be loaded from an external WAD
        # file, but I've yet to come across this

        # Half-Life 1 stored custom palette information for each mip texture,
        # so we seek past the last mip texture (and past the 256 2-byte denominator)
        # to grab the RGB values for this texture
        if self.format is BSPFormat.HL:
            customPalette = []
            stream.seek(baseOffset + offset8 + ((width//8) * (height//8)) + 2)
            for p in range(0, 256):
                customPalette.append(struct.unpack("BBB", stream.read(3)))

        # Skip to the correct byte offset for mip level 1
        stream.seek(baseOffset + offset1)

        # Grab the raw pixel data
        numPixels = width * height
        pixels = []
        for p in range(0, numPixels):
            index, = struct.unpack("B", stream.read(1))
            if self.format is not BSPFormat.HL:
                pixels.append(self.palette[index])
            else:
                pixels.append(customPalette[index])

        print("Parsed " + str(name))
        return Texture(pixels, width, height, name)