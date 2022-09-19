import os, io, struct, math

from bsp2obj.helpers import *
from bsp2obj.pak import *
from bsp2obj.image import *
from bsp2obj.constants import * 

from PIL import Image

class Edge(object):
    def __init__(self, vert1, vert2):
        self.vert1 = vert1
        self.vert2 = vert2

class Face(object):
    def __init__(self, firstEdgeIndex, numEdges, texInfoID):
        self.firstEdgeIndex = firstEdgeIndex
        self.numEdges = numEdges
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

class TextureGroup(object):
    def __init__(self, vertexIndices, uvIndices, normalIndices):
        self.vertexIndices = vertexIndices
        self.uvIndices = uvIndices
        self.normalIndices = normalIndices

class LumpHeader(object):
    def __init__(self, offset, length):
        self.offset = offset
        self.length = length

    def __repr__(self):
        return "LumpHeader (offset: {}, length: {})".format(self.offset, self.length)

class BSP(object):
    def __init__(self, data, paks, palettePath, game):
        self.data = data
        self.paks = paks
        self.game = game

        numLumps = 0

        identStr, = struct.unpack("4s", data.read(4))

        if game is Game.Q2 or game is Game.KINGPIN or game is Game.DAIKATANA:
            numLumps = 19
        else:
            # GoldSrc-era BSP files don't have any ident value, so we assume this is Quake
            # In which case we need to rewind 4 bytes as we've just read the BSP version accidentally 
            data.seek(data.tell()-4)
            numLumps = 15

        version, = struct.unpack("I", data.read(4))

        print("BSP version {}".format(version))

        self.palette = TextureLoader.loadFromPath(palettePath, paks)
        if self.palette is None:
            raise KeyError("Unable to find palette file `%s` in PAK file"%(palettePath))

        # Parse this BSPs lumps
        lumps = []
        for i in range(0, numLumps):
            header = LumpHeader(0, 0)
            header.offset, header.length = struct.unpack("II", data.read(8))
            lumps.append(header)

        if game is Game.Q1 or game is Game.HL1:
            self.textures = self.parseTextures(lumps[2])
            self.vertices = self.parseVertices(lumps[3])
            self.texInfos = self.parseTextureInfo(lumps[6])
            self.faces = self.parseFaces(lumps[7])
            self.edges = self.parseEdges(lumps[12])
            self.lEdges = self.parseLEdges(lumps[13])
        else:
            self.vertices = self.parseVertices(lumps[2])
            self.texInfos = self.parseTextureInfo(lumps[5])
            self.faces = self.parseFaces(lumps[6])
            self.edges = self.parseEdges(lumps[11])
            self.lEdges = self.parseLEdges(lumps[12])

            self.textures = {}
            for texInfo in self.texInfos:
                if texInfo.name not in self.textures:
                    for extension in ["wal", "tga"]:
                        path = "textures/" + texInfo.name + "." + extension

                        data = self.paks.dataForEntry(path)
                        if data is not None:
                            if extension == "wal":
                                self.textures[texInfo.name] = TextureLoader.loadWAL(self.game, data, self.palette)
                            else:
                                self.textures[texInfo.name] = TextureLoader.loadFromPath(path, self.paks)

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
            e = face.firstEdgeIndex
            uvOffset = len(uvs)

            # Since we've already got a master list of vertices we need to iterate over our
            # edge list and generate vertex indices. We'll also generate UV coordinates for
            # each vertex as we go...
            for i in range(0, face.numEdges):
                if(self.lEdges[face.firstEdgeIndex + i] < 0):
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
        outputPath = createFolderStructure(outputFileName) + outputFileName

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
        if self.game is not Game.Q2 and self.game is not Game.KINGPIN and self.game is not Game.DAIKATANA:
            for texture in self.textures:
                texture.save(outputFileName + "/" + texture.name + ".png")
        else:
            textureList = self.textures.values()
            for texture in textureList:
                texture.save(outputFileName + "/" + texture.name + ".png")

        print("OBJ saved to `%s`"%(outputFileName))

    def parseVertices(self, lump):
        self.data.seek(lump.offset)

        vertices = []
        for i in range(0, lump.length//12):
            vertex = struct.unpack("fff", self.data.read(12))
            vertices.append(Vector3.swizzle(vertex[0], vertex[1], vertex[2]))

        return vertices

    def parseLEdges(self, lump):
        self.data.seek(lump.offset)

        edgeList = []
        for i in range(0, lump.length//4):
            index, = struct.unpack("i", self.data.read(4))
            edgeList.append(index)

        return edgeList

    def parseEdges(self, lump):
        self.data.seek(lump.offset)

        edges = []
        for i in range(0, lump.length//4):
            data = struct.unpack("HH", self.data.read(4))
            edges.append(Edge(data[0], data[1]))
    
        return edges

    def parseFaces(self, lump):
        self.data.seek(lump.offset)

        faces = []
        for i in range(0, lump.length//20):
            self.data.read(4) # skip plane index

            data = struct.unpack("ihh", self.data.read(8))
            faces.append(Face(data[0], data[1], data[2]))

            self.data.read(8) # skip lightmap info
        
        return faces

    def parseTextureInfo(self, lump):
        self.data.seek(lump.offset)

        length = 40
        if self.game is Game.Q2 or self.game is Game.KINGPIN or self.game is Game.DAIKATANA:
            length = 76

        texInfos = []
        for i in range(0, lump.length//length):
            name = None

            # GoldSrc BSP files didn't contain texture names as part of the texInfo lump
            # because all textures were contained within the BSP file itself. When future
            # versions of the engine made it possible to store texture data outside of BSP files
            # it became necessary to pack texInfo with texture names for external look-up
            if self.game is Game.Q2 or self.game is Game.KINGPIN or self.game is Game.DAIKATANA:
                data = struct.unpack("ffffffffII32sI", self.data.read(length))
                name = c_char_p(data[10]).value
                name = bytesToString(name)
            else:
                data = struct.unpack("ffffffffII", self.data.read(length))

            uAxis = Vector3.swizzle(data[0], data[1], data[2])
            uOffset = data[3]
            vAxis = Vector3.swizzle(data[4], data[5], data[6])
            vOffset = data[7]
            textureID = data[8]
            animated = data[9]

            texInfos.append(TextureInfo(name, uAxis, uOffset, vAxis, vOffset, textureID, animated))

        return texInfos

    def parseTextures(self, lump):
        if self.palette is None:
            raise ValueError("Attempt to parse a texture without an associated palette")

        self.data.seek(lump.offset)

        numTextures, = struct.unpack("I", self.data.read(4))
        offsets = []

        for i in range (0, numTextures):
            textureOffset, = struct.unpack("I", self.data.read(4))
            offsets.append(textureOffset)

        textures = []
        for i in range(0, numTextures):
            self.data.seek(lump.offset + offsets[i])
            textures.append(TextureLoader.loadWAL(self.game, self.data, self.palette))

        return textures