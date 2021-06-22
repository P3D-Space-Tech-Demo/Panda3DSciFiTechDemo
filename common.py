from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.interval.IntervalGlobal import *
import random
import array
import os

load_prc_file_data("",
"""
sync-video false
win-size 1680 1050
# win-size 2560 1440
# fullscreen true
framebuffer-multisample 1
multisamples 4
""")


base = ShowBase()
