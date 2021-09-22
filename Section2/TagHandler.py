
import common

def handleGeometryTags(np):
    glowingThings = np.findAllMatches("**/=glowShader")
    for glowingThing in glowingThings:
        common.make_glowing_np(glowingThing)

    billboardThings = np.findAllMatches("**/=billboardEye")
    for billboardThing in billboardThings:
        billboardThing.setBillboardPointEye()

    billboardThings = np.findAllMatches("**/=billboardAxis")
    for billboardThing in billboardThings:
        billboardThing.setBillboardAxis()