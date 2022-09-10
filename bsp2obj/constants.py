from enum import Enum

class BSPFormat(Enum):
    GSRC = 1 # Quake
    IBSP = 2 # Quake 2 (also used for Quake 3, but that's unsupported right now)
    HL = 3 # Half-Life
