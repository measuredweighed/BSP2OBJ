#!/usr/bin/env python

from bsp2obj.bsp import *
import os, getopt, sys, traceback

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:p:m:c:d:")

        pakPath = None
        palettePath = None
        bspPath = None
        outputPath = "output"
        pakDumpPattern = None

        for opt, arg in opts:
            if opt in "-p":
                pakPath = arg
            elif opt in "-m":
                bspPath = arg
            elif opt in "-c":
                palettePath = arg
            elif opt in "-o":
                outputPath = arg
            elif opt in "-d":
                pakDumpPattern = arg

        if bspPath is None:
            raise ValueError("Failed to provide a BSP filepath")

        if palettePath is None:
            raise ValueError("Failed to provide a palette filepath")

        if pakPath is not None and bspPath is not None:

            path = os.path.join(sys.path[0], pakPath)
            with open(path, "rb") as f:
                stream = BinaryStream(f)

                pak = PAK(stream)

                if pakDumpPattern is not None:
                    pak.dumpContents(pakDumpPattern)

                if bspPath in pak.directory:
                    stream.seek(pak.directory[bspPath][0])

                    bsp = BSP(stream, pak, palettePath)
                    bsp.saveOBJ(outputPath)
                else:
                    raise KeyError("Unable to find `%s` in provided PAK file" %(bspPath))

        # If we've been passed a BSP path, but not a PAK path, we can assume
        # we're loading the likes of a Half-Life BSP where resource files
        # should instead be looked up via the filesystem (rather than being
        # tightly coupled with an associated PAK file)
        elif bspPath is not None:

            with open(bspPath, "rb") as f:
                stream = BinaryStream(f)

                bsp = BSP(stream, None, palettePath)
                bsp.saveOBJ(outputPath)        


    except getopt.GetoptError:
        print("Invalid opt usage")

    except Exception as e:
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

        exception_str = "Traceback (most recent call last):\n"
        exception_str += "".join(exception_list)
        # Removing the last \n
        exception_str = exception_str[:-1]
        print(exception_str)