
from direct.showbase.ShowBase import ShowBase

from panda3d.core import WindowProperties, VirtualFileSystem, Filename, TextNode
from panda3d.core import OrthographicLens
from panda3d.core import Vec4, Vec3, Vec2, NodePath, PandaNode, Quat, Shader, DirectionalLight
from direct.gui.DirectGui import *

# Copied from "common.py", in order to avoid that file's ShowBase initialsation
vert_shader = "../Assets/Shared/shaders/pbr_shader_v.vert"
frag_shader = "../Assets/Shared/shaders/pbr_shader_f.frag"
invert_vert = "../Assets/Shared/shaders/pbr_shader_v_invert.vert"
invert_frag = "../Assets/Shared/shaders/pbr_shader_f_invert.frag"
metal_shader = Shader.load(Shader.SL_GLSL, invert_vert, invert_frag)
scene_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)
# /Copied

class Game(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        properties = WindowProperties()
        properties.setSize(1280, 720)
        self.win.requestProperties(properties)

        self.disableMouse()

        self.exitFunc = self.cleanup

        self.accept("escape", self.userExit)
        self.accept("mouse1", self.mouseDown)
        self.accept("mouse1-up", self.mouseUp)
        self.accept("mouse3", self.rightMouseDown)
        self.accept("mouse3-up", self.rightMouseUp)

        self.taskMgr.add(self.update, "update")

        self.directoryEntry = DirectEntry(parent = self.a2dTopLeft,
                                          initialText = "../Assets/",
                                          scale = 0.05,
                                          width = 15,
                                          text_align = TextNode.ALeft,
                                          pos = (0.025, 0, -0.1)
                                          )
        self.scanBtn = DirectButton(parent = self.a2dTopLeft,
                                    text = "Scan Dir.",
                                    scale = 0.07,
                                    text_align = TextNode.ALeft,
                                    pos = (0.8, 0, -0.105),
                                    command = self.scanDirectory)

        self.scroller = DirectScrolledFrame(parent = self.a2dTopLeft,
                                            frameSize = (0, 1.07, -1.825, 0),
                                            pos = (0.0225, 0, -0.15),
                                            canvasSize = (0, 1, -1, 0)
                                            )

        self.fileButtons = []

        self.fitButton = DirectButton(parent = self.a2dBottomRight,
                                     text = "Fit Model\nTo View",
                                     pos = (-0.0225, 0, 0.105),
                                     text_align = TextNode.ARight,
                                     command = self.fitModel,
                                     scale = 0.07)

        self.shaderBaseButton = DirectButton(parent = self.a2dTopRight,
                                             text = "Shader:\nScene",
                                             pos = (-0.0225, 0, -0.105),
                                             text_align = TextNode.ARight,
                                             command = self.setSceneShader,
                                             extraArgs = [scene_shader],
                                             scale = 0.07)

        self.shaderMetalButton = DirectButton(parent = self.a2dTopRight,
                                             text = "Shader:\nMetal",
                                             pos = (-0.3225, 0, -0.105),
                                             text_align = TextNode.ARight,
                                             command = self.setSceneShader,
                                             extraArgs = [metal_shader],
                                             scale = 0.07)

        self.turntableCheck = DirectCheckButton(parent = self.a2dBottomLeft,
                                                text = "Turntable\nRotation",
                                                pos = (1.07 + 0.1, 0, 0.105),
                                                text_align = TextNode.ALeft,
                                                command = self.setTurntableState,
                                                scale = 0.07)

        self.turnTableSlider = DirectSlider(parent = self.a2dBottomLeft,
                                            text = "Turntable Speed",
                                            pos = (1.07 + 0.925, 0, 0.07),
                                            text_pos = (0, 0.095),
                                            value = 50,
                                            range = (0, 200),
                                            scale = 0.5,
                                            text_scale = 0.125)

        self.modelBase = self.render.attachNewNode(PandaNode("model base"))
        self.modelBase.setPos(11.7, 40, 0)
        self.currentModel = None

        self.mouseDownPos = None
        self.rotationScalar = 100
        self.baseQuat = Quat()

        self.rightMouseDownPos = None
        self.scalingScalar = 3
        self.baseScale = 1

        self.turnTableActive = False
        self.turnTableAxis = Vec3(0, -0.4, 1).normalized()

        light = DirectionalLight("directional light")
        light.setColor(Vec4(1, 1, 1, 1)*3.142)
        self.lightNP = self.modelBase.attachNewNode(light)
        self.lightNP.setHpr(135, -45, 0)
        self.modelBase.setLight(self.lightNP)

        light = DirectionalLight("directional light")
        light.setColor(Vec4(0.4, 0.45, 0.6, 1)*3.142)
        self.lightNP2 = self.modelBase.attachNewNode(light)
        self.lightNP2.setHpr(-135, 45, 0)
        self.modelBase.setLight(self.lightNP2)

        lens = OrthographicLens()
        lens.setFilmSize(Vec2(70, 70))
        lens.setNearFar(-1000, 10000)
        self.camNode.setLens(lens)
        self.camLens = lens

    def scanDirectory(self):
        for btn in self.fileButtons:
            btn.destroy()
            btn.removeNode()
        self.fileButtons = []

        canvas = self.scroller.getCanvas()

        directory = self.directoryEntry.get()
        fileSystem = VirtualFileSystem.getGlobalPtr()
        fileList = self.scanDirectoryInternal(fileSystem, directory)
        fileList.sort(key = lambda x: x.getBasename())
        zPos = -0.1
        for file in fileList:
            btn = DirectButton(parent = canvas,
                               pos = (0.05, 0, zPos),
                               text = file.getBasename(),
                               scale = 0.05,
                               command = self.loadModel,
                               pad = (0.1, 0.1),
                               text_align = TextNode.ALeft,
                               extraArgs = [file])
            self.fileButtons.append(btn)
            zPos -= 0.1

        self.scroller["canvasSize"] = (0, 1, zPos, 0)

    def scanDirectoryInternal(self, fileSystem, directory):
        result = []

        files = fileSystem.scanDirectory(directory)
        if files is not None:
            for file in files:
                fileName = file.getFilename()
                if file.isDirectory():
                    result += self.scanDirectoryInternal(fileSystem, fileName)
                else:
                    ext = fileName.getExtension()
                    if ext == "egg" or ext == "bam" or ext == "gltf" or ext == "pz":
                        result.append(fileName)

        return result

    def loadModel(self, file):
        if self.currentModel is not None:
            self.currentModel.removeNode()

        model = self.loader.loadModel(file)
        model.reparentTo(self.modelBase)

        self.currentModel = model

    def fitModel(self):
        if self.currentModel is not None:
            bounds = self.currentModel.getTightBounds()
            w = abs(bounds[1].x - bounds[0].x)
            h = abs(bounds[1].z - bounds[0].z)
            l = abs(bounds[1].y - bounds[0].y)
            largestDimension = max(max(w, l), h)
            scalar = 35 / largestDimension
            self.currentModel.setScale(scalar)

    def setTurntableState(self, state):
        self.turnTableActive = state

    def setSceneShader(self, shaderRef):
        self.modelBase.setShader(shaderRef)

    def mouseDown(self):
        if self.mouseWatcherNode.hasMouse():
            self.mouseDownPos = Vec2(self.mouseWatcherNode.getMouse())
        else:
            self.mouseDownPos = Vec2(0, 0)
        self.baseQuat = self.modelBase.getQuat(self.render)

    def mouseUp(self):
        self.mouseDownPos = None

    def rightMouseDown(self):
        if self.mouseWatcherNode.hasMouse():
            self.rightMouseDownPos = Vec2(self.mouseWatcherNode.getMouse())
        else:
            self.rightMouseDownPos = Vec2(0, 0)
        self.baseScale = self.currentModel.getScale(self.render)

    def rightMouseUp(self):
        self.rightMouseDownPos = None

    def update(self, task):
        if self.mouseDownPos is not None:
            if self.mouseWatcherNode.hasMouse():
                mousePos = self.mouseWatcherNode.getMouse()
                diff = mousePos - self.mouseDownPos
                offset = diff.length()
                if offset > 0.000001:
                    quat = Quat()
                    quat.setFromAxisAngle(offset*self.rotationScalar, Vec3(-diff.y, 0, diff.x).normalized())
                    self.modelBase.setQuat(self.render, self.baseQuat * quat)

        if self.rightMouseDownPos is not None:
            if self.mouseWatcherNode.hasMouse():
                mousePos = self.mouseWatcherNode.getMouse()
                diff = mousePos - self.rightMouseDownPos
                offset = diff.length()
                if offset > 0.000001:
                    self.currentModel.setScale(self.render, self.baseScale * pow(2, -diff.y * self.scalingScalar))

        if self.turnTableActive:
            quat = Quat()
            quat.setFromAxisAngle(self.turnTableSlider.getValue()*globalClock.getDt(), self.turnTableAxis)
            self.modelBase.setQuat(self.render, self.modelBase.getQuat(self.render) * quat)

        return task.cont

    def cleanup(self):
        if self.currentModel is not None:
            self.currentModel.removeNode()

game = Game()
game.run()
