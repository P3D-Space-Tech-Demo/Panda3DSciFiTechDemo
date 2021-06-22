
import common

class Spawner():
    def __init__(self, data, pos, h, objIsEnemy):
        if isinstance(data, tuple):
            self.spawnObj = data[0](*data[1:])
        else:
            self.spawnObj = data()

        self.spawnObj.root.setPos(common.base.render, pos)
        self.spawnObj.root.setH(common.base.render, h)
        self.spawnObj.root.detachNode()

        self.objIsEnemy = objIsEnemy

        self.isReady = True

    def destroy(self):
        if self.spawnObj is not None:
            self.spawnObj.destroy()
            self.spawnObj = None

        self.isReady = False