#!/usr/bin/env python

from bsp2obj.bsp import *
from bsp2obj.pak import *
import os, getopt, sys, traceback

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:p:m:c:d:")

        pakPaths = []
        palettePath = None
        bspPath = None
        outputPath = "output"
        pakDumpPattern = None

        for opt, arg in opts:
            if opt in "-p":
                pakPaths.append(arg)
            elif opt in "-m":
                bspPath = arg
            elif opt in "-c":
                palettePath = arg
            elif opt in "-o":
                outputPath = arg
            elif opt in "-d":
                pakDumpPattern = arg

        paks = PAKCollection(pakPaths)

        if pakDumpPattern is not None:
            paks.dumpContents(pakDumpPattern)
            os._exit(1)

        if bspPath is None:
            raise ValueError("Failed to provide a BSP filepath")

        if palettePath is None:
            raise ValueError("Failed to provide a palette filepath")

        if len(paks.list) > 0:

            pak, bspEntry = paks.entryForName(bspPath)
            if bspEntry is not None:
                pak.stream.seek(bspEntry[0])

                bsp = BSP(pak.stream, paks, palettePath)
                bsp.saveOBJ(outputPath)
            else:
                raise KeyError("Unable to find `%s` in provided PAK file" %(bspPath))

        # If we've been passed a BSP path, but not a PAK path, we can assume
        # we're loading the likes of a Half-Life BSP where resource files
        # should instead be looked up via the filesystem (rather than being
        # tightly coupled with an associated PAK file)
        else:

            with open(bspPath, "rb") as f:
                stream = BinaryStream(f)

                bsp = BSP(stream, paks, palettePath)
                bsp.saveOBJ(outputPath)        

        paks.closeAll()

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