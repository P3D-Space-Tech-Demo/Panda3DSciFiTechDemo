
from panda3d.core import CardMaker, Shader, Vec3, Vec2, NodePath, ColorBlendAttrib

from Section2.Common import Common

import random

class Explosion():
    cardMaker = None

    @staticmethod
    def getCard():
        if Explosion.cardMaker is None:
            Explosion.cardMaker = CardMaker("explosion maker")
            Explosion.cardMaker.setFrame(-1, 1, -1, 1)

        explosionCard = NodePath(Explosion.cardMaker.generate())

        return explosionCard

    def __init__(self, size, shaderName, shaderInputs, inputTextureName, randomVal1, randomVal2):
        self.explosionCard = Explosion.getCard()
        self.explosionCard.setScale(size)
        self.explosionCard.setBin("unsorted", 1)
        self.explosionCard.setDepthWrite(False)
        self.explosionCard.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
        self.explosionCard.setBillboardPointEye()

        shader = Shader.load(Shader.SL_GLSL,
                             "Assets/Section2/shaders/{0}Vertex.glsl".format(shaderName),
                             "Assets/Section2/shaders/{0}Fragment.glsl".format(shaderName))
        self.explosionCard.setShader(shader)

        for inputName, inputValue in shaderInputs.items():
            self.explosionCard.setShaderInput(inputName, inputValue)

        self.explosionCard.setShaderInput("sourceTex1", Common.framework.showBase.loader.loadTexture("Assets/Section2/tex/{0}1.png".format(inputTextureName)))
        self.explosionCard.setShaderInput("sourceTex2", Common.framework.showBase.loader.loadTexture("Assets/Section2/tex/{0}2.png".format(inputTextureName)))

        self.explosionCard.setShaderInput("randomisation1", randomVal1)
        self.explosionCard.setShaderInput("randomisation2", randomVal2)

        self.calcFullDuration(shaderInputs)

        self.startTime = -1000
        self.explosionCard.setShaderInput("startTime", self.startTime)

        self.velocity = Vec3(0, 0, 0)

    def calcFullDuration(self, shaderInputs):
        self.duration = 0
        if "duration" in shaderInputs:
            self.duration += shaderInputs["duration"]
        if "starDuration" in shaderInputs:
            self.duration += shaderInputs["starDuration"]

    def activate(self, velocity, pos):
        self.startTime = globalClock.getRealTime()
        self.explosionCard.setShaderInput("startTime", self.startTime)
        self.velocity = velocity
        self.explosionCard.reparentTo(Common.framework.showBase.render)
        self.explosionCard.setPos(pos)

    def update(self, dt):
        self.explosionCard.setPos(self.explosionCard.getPos() + self.velocity*dt)

    def isAlive(self):
        return (globalClock.getRealTime() - self.startTime) < (self.duration)

    def cleanup(self):
        if self.explosionCard is not None:
            self.explosionCard.removeNode()
            self.explosionCard = None