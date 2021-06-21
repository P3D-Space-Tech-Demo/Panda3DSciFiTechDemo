
from Section3.Common import Common

class Spawner():
    def __init__(self, data, pos, h, objIsEnemy):
        if isinstance(data, tuple):
            self.spawnObj = data[0](*data[1:])
        else:
            self.spawnObj = data()

        self.spawnObj.root.setPos(Common.framework.showBase.render, pos)
        self.spawnObj.root.setH(Common.framework.showBase.render, h)
        self.spawnObj.root.detachNode()

        self.objIsEnemy = objIsEnemy

        self.isReady = True

    def cleanup(self):
        if self.spawnObj is not None:
            self.spawnObj.cleanup()
            self.spawnObj = None

        self.isReady = False