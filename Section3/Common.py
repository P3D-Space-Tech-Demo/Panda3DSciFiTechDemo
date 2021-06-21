
from direct.particles.ParticleEffect import ParticleEffect

class Common:
    framework = None

    @staticmethod
    def loadParticles(fileName):
        extension = "ptf"
        directory = "Particles/"
        if not fileName.endswith(".{0}".format(extension)):
            fileName = "{0}.{1}".format(fileName, extension)
        fileName = "{0}{1}".format(directory, fileName)

        particleEffect = ParticleEffect()
        particleEffect.loadConfig(fileName)
        return particleEffect

    @staticmethod
    def initialise():
        base.enableParticles()