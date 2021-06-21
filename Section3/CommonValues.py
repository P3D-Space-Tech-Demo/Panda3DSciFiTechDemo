
from panda3d.core import BitMask32


TAG_OWNER = "owner"

MASK_WALLS = BitMask32(1)
MASK_FLOORS = BitMask32(2)

MASK_INTO_ENEMY = BitMask32(4)
MASK_INTO_PLAYER = BitMask32(8)

MASK_FROM_PLAYER = BitMask32(16)