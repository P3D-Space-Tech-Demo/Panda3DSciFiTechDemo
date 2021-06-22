from common import base
from gui import GUI

from Section1 import section1
from Section2 import Section2_
from Section3 import Section3_

from Ships import shipSpecs

base.disable_mouse()


class Demo:

    def __init__(self):
        base.exitFunc = self.cleanup

        sections = [section1, Section2_, Section3_, section1]

        GUI(sections, shipSpecs, self.quit)

    def cleanup(self):
        pass

    def quit(self):
        self.cleanup()

        base.userExit()


Demo()

base.run()
