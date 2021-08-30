from common import *
from .intro_portal import SphericalPortalSystem


class Intro:

    def __init__(self):

        lights = []
        pos = Point3()
        self.portal_sys = SphericalPortalSystem(lights, pos)
        base.task_mgr.add(self.play, "play_intro")

    def play(self, task):

        return task.cont

    def destroy(self):

        self.portal_sys.destroy()
        base.task_mgr.remove("play_intro")
