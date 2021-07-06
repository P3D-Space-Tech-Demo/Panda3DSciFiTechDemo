
from direct.showbase.ShowBase import ShowBase

from panda3d.core import WindowProperties, TextNode, Vec4, Vec3, Vec2, Filename, Texture
from direct.stdpy.file import *
from direct.gui.DirectGui import *

import Section1.section1 as Section1
import Section2.Section2 as Section2
import Section3.Section3 as Section3
import Section2.Section2 as Section4

import common

from Ships import shipSpecs

TAG_PREVIOUS_MENU = "predecessor"

OPTION_FILE_DIR = "."
OPTION_FILE_NAME = "options.dat"

class Game():
    BUTTON_SIZE_LARGE = 0
    BUTTON_SIZE_SMALL = 1

    #fancyFont = loader.loadFont("Assets/Shared/fonts/Excluded/ExcludedItalic.ttf")
    #italiciseFont = False

    #fancyFont = loader.loadFont("Assets/Shared/fonts/SavingsBond/savings_bond/SAVINGSB_.TTF")
    #italiciseFont = True

    fancyFont = loader.loadFont("Assets/Shared/fonts/cinema-gothic-nbp-font/CinemaGothicNbpItalic-1ew2.ttf", pointSize = 8)
    italiciseFont = False

    @staticmethod
    def makeButton(text, command, menu, size, extraArgs = None, leftAligned = True):
        if size == Game.BUTTON_SIZE_LARGE:
            width = 20
        elif size == Game.BUTTON_SIZE_SMALL:
            width = 10
        height = 2.5

        if leftAligned:
            frame = (0, width, -height*0.5, height*0.5)
            alignment = TextNode.ALeft
            textPos = (0.9, -0.2)
            if size == Game.BUTTON_SIZE_LARGE:
                button = ""
            else:
                button = "Small"
        else:
            frame = (-width*0.5 , width*0.5, -height*0.5, height*0.5)
            alignment = TextNode.ACenter
            textPos = (0, -0.2)
            if size == Game.BUTTON_SIZE_LARGE:
                button = "SmallCentred"
            else:
                button = "SmallCentred"

        btn = DirectButton(text = text,
                           command = command,
                           scale = 0.1,
                           parent = menu,
                           text_align = alignment,
                           text_font = Game.fancyFont,
                           frameSize = frame,
                           frameColor = (1, 1, 1, 1),
                           pressEffect = False,
                           text_pos = textPos,
                           relief = DGG.FLAT,
                           frameTexture = (
                                        "Assets/Shared/tex/mainMenuBtn{0}Normal.png".format(button),
                                        "Assets/Shared/tex/mainMenuBtn{0}Click.png".format(button),
                                        "Assets/Shared/tex/mainMenuBtn{0}Highlight.png".format(button),
                                        "Assets/Shared/tex/mainMenuBtn{0}Normal.png".format(button),
                                      )
                           )
        if Game.italiciseFont:
            btn.setShear((0, 0.1, 0))
        btn.setTransparency(True)
        if extraArgs is not None:
            btn["extraArgs"] = extraArgs
        return btn

    def __init__(self):

        common.gameController = self

        properties = WindowProperties()
        properties.setSize(1280, 720)
        common.base.win.requestProperties(properties)

        common.base.win.setClearColor(Vec4(0, 0, 0, 1))

        common.base.render.set_shader(common.scene_shader)

        common.base.disableMouse()

        common.base.exitFunc = self.destroy

        common.base.accept("window-event", self.windowUpdated)

        self.currentMenu = None

        ### Main Menu

        self.mainMenuBackdrop = DirectFrame(
                                            frameSize = (-1/common.base.aspect2d.getSx(), 1/common.base.aspect2d.getSx(), -1, 1),
                                            frameTexture = "Assets/Shared/tex/mainMenuBack.png"
                                           )

        self.title1 = DirectLabel(text = "CAPTAIN PANDA",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.07,
                                 text_font = Game.fancyFont,
                                 text_fg = (0.8, 0.9, 1, 1),
                                 relief = None,
                                 pos = (0, 0, 0.8),
                                 text_align = TextNode.ALeft)
        self.title2 = DirectLabel(text = "and the",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.05,
                                 text_font = Game.fancyFont,
                                 text_fg = (0.8, 0.9, 1, 1),
                                 relief = None,
                                 pos = (0, 0, 0.75),
                                 text_align = TextNode.ALeft)
        self.title3 = DirectLabel(text = "INVASION OF THE MECHANOIDS!",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.1,
                                 text_font = Game.fancyFont,
                                 text_fg = (0.8, 0.9, 1, 1),
                                 relief = None,
                                 pos = (0, 0, 0.6625),
                                 text_align = TextNode.ALeft)

        if Game.italiciseFont:
            self.title1.setShear((0, 0.1, 0))
            self.title2.setShear((0, 0.1, 0))
            self.title3.setShear((0, 0.1, 0))

        self.mainMenuPanel = DirectFrame(
                                    frameSize = (0, 1.25, -1, 1),
                                    frameColor = (0, 0, 0, 0)
                                   )

        self.underline = DirectLabel(frameTexture = "Assets/Shared/tex/underline.png",
                                     parent = self.mainMenuPanel,
                                     relief = DGG.FLAT,
                                     frameSize = (0, 3.9, -0.0609, 0.0609),
                                     frameColor = (1, 1, 1, 1),
                                     pos = (3.5, 0, 0.6),
                                     scale = -1)
        self.underline.setTransparency(True)

        buttons = []

        btn = Game.makeButton("New Game", self.startGame, self.mainMenuPanel, Game.BUTTON_SIZE_LARGE)
        buttons.append(btn)

        btn = Game.makeButton("Chapter Selection", self.selectSection, self.mainMenuPanel, Game.BUTTON_SIZE_LARGE)
        buttons.append(btn)

        btn = Game.makeButton("Options", self.openOptions, self.mainMenuPanel, Game.BUTTON_SIZE_LARGE)
        buttons.append(btn)

        btn = Game.makeButton("Quit", self.quit, self.mainMenuPanel, Game.BUTTON_SIZE_LARGE)
        buttons.append(btn)

        buttonSpacing = 0.2125
        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing

        ### A gradient for sub-menu backgrounds

        gradient = loader.loadTexture("Assets/Shared/tex/menuGradient.png")
        gradient.setWrapU(Texture.WMClamp)
        gradient.setWrapV(Texture.WMClamp)

        ### Options Menu

        self.optionsTop = 0.35
        self.currentOptionsZ = self.optionsTop
        self.optionSpacingHeading = 0.2
        self.optionCheckSpacing = 0.25
        self.optionSliderSpacing = 0.25

        self.optionsMenu = DirectDialog(
                                        frameSize = (-1, 1, -0.85, 0.85),
                                        frameColor = (0.225, 0.325, 0.5, 0.75),
                                        fadeScreen = 0.5,
                                        pos = (0, 0, 0),
                                        frameTexture = gradient,
                                        relief = DGG.FLAT
                                       )
        self.optionsMenu.hide()

        label = DirectLabel(text = "Options",
                            parent = self.optionsMenu,
                            text_font = Game.fancyFont,
                            text_fg = (0.8, 0.9, 1, 1),
                            frameColor = (0, 0, 0.225, 1),
                            pad = (0.9, 0.3),
                            relief = DGG.FLAT,
                            scale = 0.1,
                            pos = (0, 0, 0.65)
                            )
        if Game.italiciseFont:
            label.setShear((0, 0.1, 0))

        self.optionsScroller = DirectScrolledFrame(
                                        parent = self.optionsMenu,
                                        relief = DGG.SUNKEN,
                                        scrollBarWidth = 0.1,
                                        frameSize = (-0.85, 0.95, -0.5, 0.5),
                                        frameColor = (0.225, 0.325, 0.5, 0.75),
                                        canvasSize = (-0.8, 0.8, -0.4, 0.5),
                                        frameTexture = gradient,
                                        autoHideScrollBars = False,
                                    )
        self.optionsScroller.horizontalScroll.hide()

        self.addOptionHeading("General")
        self.addOptionSlider("Music Volume", (0, 100), 1, "musicVolume", "general", 100, self.setMusicVolume)
        self.addOptionSlider("Sound Volume", (0, 100), 1, "soundVolume", "general", 100, self.setSoundVolume)
        self.addOptionHeading("Section 1")
        self.addOptionHeading("Section 2")
        Section2.addOptions()
        self.addOptionHeading("Section 3")
        self.addOptionHeading("Section 4")

        self.readOptions()

        btn = Game.makeButton("Back", self.closeOptionsMenu, self.optionsMenu, Game.BUTTON_SIZE_SMALL, leftAligned = False)
        btn.setPos(0, 0, -0.7)

        ### Section Menu

        self.sectionMenu = DirectDialog(
                                        frameSize = (0, 2, -0.85, 0.85),
                                        frameColor = (0.225, 0.325, 0.5, 0.75),
                                        fadeScreen = 0.5,
                                        pos = (0, 0, 0),
                                        relief = DGG.FLAT,
                                        frameTexture = gradient
                                       )
        self.sectionMenu.hide()

        label = DirectLabel(text = "Select a Chapter:",
                            parent = self.sectionMenu,
                            scale = 0.1,
                            text_font = Game.fancyFont,
                            text_fg = (0.8, 0.9, 1, 1),
                            frameColor = (0, 0, 0.225, 1),
                            pad = (0.9, 0.3),
                            relief = DGG.FLAT,
                            pos = (0.1925, 0, 0.65),
                            text_align = TextNode.ALeft)
        if Game.italiciseFont:
            label.setShear((0, 0.1, 0))

        buttons = []

        btn = Game.makeButton("Chapter 1 // A Warrior's Choice", self.startSection, self.sectionMenu, Game.BUTTON_SIZE_LARGE, extraArgs = [0])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 2 // Across the Night", self.startSection, self.sectionMenu, Game.BUTTON_SIZE_LARGE, extraArgs = [1])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 3 // Facing the Foe", self.startSection, self.sectionMenu, Game.BUTTON_SIZE_LARGE, extraArgs = [2])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 4 // The Escape", self.startSection, self.sectionMenu, Game.BUTTON_SIZE_LARGE, extraArgs = [3])
        buttons.append(btn)

        buttonSpacing = 0.25
        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing

        btn = Game.makeButton("Back", self.closeCurrentMenu, self.sectionMenu, Game.BUTTON_SIZE_SMALL)
        btn.setPos(0.1, 0, -0.7)

        ### Game-over menu

        self.gameOverScreen = DirectDialog(frameSize = (-0.5, 0.5, -0.7, 0.7),
                                           fadeScreen = 0.4,
                                           relief = DGG.FLAT)
        self.gameOverScreen.hide()

        label = DirectLabel(text = "Game Over!",
                            parent = self.gameOverScreen,
                            scale = 0.1,
                            pos = (0, 0, 0.55),
                            #text_font = self.font,
                            relief = None)

        btn = DirectButton(text = "Retry",
                           command = self.restartCurrentSection,
                           pos = (0, 0, 0.25),
                           parent = self.gameOverScreen,
                           scale = 0.1,
                           #text_font = self.font,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           #relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        btn = DirectButton(text = "Return to Menu",
                           command = self.openMenu,
                           pos = (0, 0, 0),
                           parent = self.gameOverScreen,
                           scale = 0.1,
                           #text_font = self.font,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           #relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        btn = DirectButton(text = "Quit",
                           command = self.quit,
                           pos = (0, 0, -0.25),
                           parent = self.gameOverScreen,
                           scale = 0.1,
                           #text_font = self.font,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           #relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        ### Section 2 ship-selection menu

        buttons = []

        self.shipSelectionMenu = DirectDialog(
                                              frameSize = (0, 2, -0.85, 0.85),
                                              fadeScreen = 0.5,
                                              frameColor = (0.225, 0.325, 0.5, 0.75),
                                              relief = DGG.FLAT,
                                              frameTexture = gradient
                                             )
        self.shipSelectionMenu.hide()
        self.shipSelectionMenu.setPythonTag(TAG_PREVIOUS_MENU, self.sectionMenu)

        label = DirectLabel(text = "Select a Ship:",
                            parent = self.shipSelectionMenu,
                            scale = 0.1,
                            text_font = Game.fancyFont,
                            text_fg = (0.8, 0.9, 1, 1),
                            frameColor = (0, 0, 0.225, 1),
                            pad = (0.9, 0.3),
                            relief = DGG.FLAT,
                            pos = (0.1925, 0, 0.65),
                            text_align = TextNode.ALeft)
        if Game.italiciseFont:
            label.setShear((0, 0.1, 0))

        btn = Game.makeButton("Light fighter", self.sectionSpecificMenuDone, self.shipSelectionMenu, Game.BUTTON_SIZE_LARGE,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[0]])
        buttons.append(btn)

        btn = Game.makeButton("Medium Interceptor", self.sectionSpecificMenuDone, self.shipSelectionMenu, Game.BUTTON_SIZE_LARGE,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[1]])
        buttons.append(btn)

        btn = Game.makeButton("Heavy Bombardment Platform", self.sectionSpecificMenuDone, self.shipSelectionMenu, Game.BUTTON_SIZE_LARGE,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[2]])
        buttons.append(btn)

        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing

        btn = Game.makeButton("Back", self.closeCurrentMenu, self.shipSelectionMenu, Game.BUTTON_SIZE_SMALL)
        btn.setPos(0.1, 0, -0.7)

        ### Section-data

        self.currentSectionIndex = 0
        self.currentSectionData = None
        self.currentSectionObject = None

        # Stores section-modules and the menu, if any, that's to be
        # shown if they're loaded without the preceding section
        # being run
        self.sections = [
            (Section1, None),
            (Section2, self.shipSelectionMenu),
            (Section3, None),
            (Section4, None),
        ]

        ### Utility

        common.base.accept("f", self.toggleFrameRateMeter)
        self.showFrameRateMeter = False

    def readOptions(self):
        try:
            fileObj = open(Filename("{0}/{1}".format(OPTION_FILE_DIR, OPTION_FILE_NAME)).toOsSpecific(), "r")
            for line in fileObj:
                sectionID, optionID, optionValueStr = line.split("|")
                sectionID = sectionID.strip()
                optionID = optionID.strip()
                optionValueStr = optionValueStr.strip()
                optionValue = self.parseOptionVal(optionValueStr)
                common.options[sectionID][optionID] = optionValue
                setter = common.optionWidgets[sectionID][optionID][0]
                setter(optionID, sectionID, optionValue)
            fileObj.close()
        except FileNotFoundError as e:
            pass

    def updateSlider(self, optionID, sectionID, value):
        slider = common.optionWidgets[sectionID][optionID][1]
        slider["value"] = value

    def updateCheck(self, optionID, sectionID, value):
        check = common.optionWidgets[sectionID][optionID][1]
        check["indicatorValue"] = value
        check.setIndicatorValue()

    def parseOptionVal(self, valueStr):
        result = 0
        if "," in valueStr:
            valueList = valueStr.split(",")
            valueList = [self.parseOptionVal(subStr) for subStr in valueList]
            if len(valueList) == 4:
                result = Vec4(*valueList)
            elif len(valueList) == 3:
                result = Vec3(*valueList)
            elif len(valueList) == 2:
                result = Vec2(*valueList)
            else:
                result = None
        elif valueStr.lower() == "true":
            result = True
        elif valueStr.lower() == "false":
            result = False
        else:
            try:
                result = int(valueStr)
            except ValueError:
                try:
                    result = float(valueStr)
                except ValueError:
                    result = None

        return result

    def getOptionValueString(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, Vec4):
            return "{0}, {1}, {2}, {3}".format(value.x, value.y, value.z, value.w)
        if isinstance(value, Vec3):
            return "{0}, {1}, {2}".format(value.x, value.y, value.z)
        if isinstance(value, Vec2):
            return "{0}, {1}".format(value.x, value.y)
        return str(value)

    def writeOptions(self):
        fileObj = open(Filename("{0}/{1}".format(OPTION_FILE_DIR, OPTION_FILE_NAME)).toOsSpecific(), "w")
        for sectionKey, section in common.options.items():
            for optionKey, option in section.items():
                fileObj.write("{0} | {1} | {2}\n".format(sectionKey, optionKey, self.getOptionValueString(option)))
        fileObj.close()

    def setOptionData(self, optionID, sectionID, defaultValue, setCallback = None):
        if not sectionID in common.optionCallbacks:
            common.optionCallbacks[sectionID] = {}
        common.optionCallbacks[sectionID][optionID] = setCallback

        if not sectionID in common.options:
            common.options[sectionID] = {}
        common.options[sectionID][optionID] = defaultValue

    def setOptionWidgets(self, optionID, sectionID, widgetList):
        if not sectionID in common.optionWidgets:
            common.optionWidgets[sectionID] = {}
        common.optionWidgets[sectionID][optionID] = widgetList

    def setOptionValue(self, value, optionID, sectionID):
        common.options[sectionID][optionID] = value

        setCallback = common.optionCallbacks[sectionID][optionID]
        if setCallback is not None:
            setCallback(value)

    def setOptionValueFromSlider(self, args):
        optionID, sectionID, slider = args
        val = slider.getValue()

        self.setOptionValue(val, optionID, sectionID)

    def addOptionSlider(self, text, rangeTuple, pageSize, optionID, sectionID, defaultValue, setCallback = None):
        self.setOptionData(optionID, sectionID, defaultValue, setCallback)

        slider = DirectSlider(text = text,
                              parent = self.optionsScroller.getCanvas(),
                              scale = 0.65,
                              text_pos = (0, 0.1),
                              text_scale = 0.1,
                              pos = (0, 0, self.currentOptionsZ),
                              command = self.setOptionValueFromSlider,
                              thumb_image = (
                                  "Assets/Shared/tex/mainMenuSliderThumbNormal.png",
                                  "Assets/Shared/tex/mainMenuSliderThumbClick.png",
                                  "Assets/Shared/tex/mainMenuSliderThumbHighlight.png",
                                  "Assets/Shared/tex/mainMenuSliderThumbNormal.png"
                              ),
                              thumb_image_scale = 0.1125,
                              thumb_frameSize = (-0.06, 0.06, -0.09, 0.09),
                              thumb_frameColor = (1, 1, 1, 1),
                              thumb_relief = None,
                              thumb_pressEffect = False,
                              value = defaultValue,
                              range = rangeTuple,
                              frameColor = (0.05, 0.05, 0.125, 1),
                              pageSize = pageSize,
                              orientation = DGG.HORIZONTAL)
        slider["extraArgs"] = [optionID, sectionID, slider],
        slider.setTransparency(True)
        label1 = DirectLabel(text = str(rangeTuple[0]),
                             scale = 0.06,
                             text_font = Game.fancyFont,
                             text_fg = (0.8, 0.9, 1, 1),
                             frameTexture = "Assets/Shared/tex/mainMenuSliderCapLeft.png",
                             frameSize = (-1.15, 0.85, -1, 1),
                             pos = (-0.7, 0, self.currentOptionsZ),
                             text_pos = (0, 0.8),
                             parent = self.optionsScroller.getCanvas())
        label1.setTransparency(True)
        label2 = DirectLabel(text = str(rangeTuple[1]),
                             scale = 0.06,
                             text_font = Game.fancyFont,
                             text_fg = (0.8, 0.9, 1, 1),
                             frameTexture = "Assets/Shared/tex/mainMenuSliderCapRight.png",
                             frameSize = (-0.85, 1.15, -1, 1),
                             pos = (0.7, 0, self.currentOptionsZ),
                             text_pos = (0, 0.8),
                             parent = self.optionsScroller.getCanvas())
        label2.setTransparency(True)
        self.setOptionWidgets(optionID, sectionID, [self.updateSlider, slider, label1, label2])

        self.currentOptionsZ -= self.optionSliderSpacing
        self.updateOptionsCanvasSize()

    def addOptionCheck(self, text, optionID, sectionID, defaultValue, setCallback = None):
        self.setOptionData(optionID, sectionID, defaultValue, setCallback)

        check = DirectCheckButton(text = text,
                                  scale = 0.075,
                                  text_align = TextNode.ACenter,
                                  parent = self.optionsScroller.getCanvas(),
                                  pos = (0, 0, self.currentOptionsZ),
                                  command = self.setOptionValue,
                                  text_font = Game.fancyFont,
                                  text_fg = (0.8, 0.9, 1, 1),
                                  boxPlacement = "below",
                                  boxRelief = None,
                                  boxImageScale = (4, 1, 1),
                                  pressEffect = False,
                                  boxImage = ("Assets/Shared/tex/mainMenuCheckEmpty.png", "Assets/Shared/tex/mainMenuCheckFull.png", None),
                                  relief = None,
                                  extraArgs = [optionID, sectionID],
                                  indicatorValue = defaultValue)
        check.indicator.setTransparency(True)

        self.setOptionWidgets(optionID, sectionID, [self.updateCheck, check])

        self.currentOptionsZ -= self.optionCheckSpacing
        self.updateOptionsCanvasSize()

    def addOptionRadioSet(self, text, buttonLabels, optionID, sectionID, defaultValue, setCallback = None):
        self.setOptionData(optionID, sectionID, defaultValue, setCallback)

    def addOptionMenu(self, text, menuItems, optionID, sectionID, defaultValue, setCallback = None):
        self.setOptionData(optionID, sectionID, defaultValue, setCallback)

    def addOptionHeading(self, text):
        self.currentOptionsZ -= self.optionSpacingHeading*0.5
        label = DirectLabel(text = text,
                            text_align = TextNode.ACenter,
                            text_font = Game.fancyFont,
                            text_fg = (0.8, 0.9, 1, 1),
                            scale = 0.1,
                            frameColor = (0, 0, 0.225, 1),
                            pad = (0.7, 0.2),
                            relief = DGG.FLAT,
                            parent = self.optionsScroller.getCanvas(),
                            pos = (0, 0, self.currentOptionsZ))
        if Game.italiciseFont:
            label.setShear((0, 0.1, 0))
        self.currentOptionsZ -= self.optionSpacingHeading
        self.updateOptionsCanvasSize()

    def updateOptionsCanvasSize(self):
        self.optionsScroller["canvasSize"] = (-0.85, 0.85, self.currentOptionsZ, 0.5)

    def setMusicVolume(self, vol):
        common.base.musicManager.setVolume(vol)

    def setSoundVolume(self, vol):
        common.base.sfxManagerList[0].setVolume(vol)

    def toggleFrameRateMeter(self):
        self.showFrameRateMeter = not self.showFrameRateMeter

        common.base.setFrameRateMeter(self.showFrameRateMeter)

    def windowUpdated(self, window):
        common.base.windowEvent(window)
        self.mainMenuBackdrop["frameSize"] = (-1/common.base.aspect2d.getSx(), 1/common.base.aspect2d.getSx(),
                                              -1/common.base.aspect2d.getSz(), 1/common.base.aspect2d.getSz())
        self.mainMenuPanel.setX(common.base.render2d, -1)
        self.mainMenuPanel["frameSize"] = (0, 1.25, -1/common.base.aspect2d.getSz(), 1/common.base.aspect2d.getSz())
        self.sectionMenu.setPos(common.base.render, -0.8, 0, 0)
        self.shipSelectionMenu.setPos(common.base.render, -0.6, 0, 0)

    def openMenu(self):
        self.currentSectionIndex = 0
        self.currentSectionData = None

        self.gameOverScreen.hide()
        self.mainMenuBackdrop.show()
        self.mainMenuPanel.show()

        self.currentMenu = None

    def openOptions(self):
        self.optionsMenu.show()
        self.currentMenu = self.optionsMenu

    def startGame(self):
        self.startSection(0)

    def startSection(self, index, data = None):
        self.sectionMenu.hide()

        specificMenu = self.sections[index][1]
        if specificMenu is not None and data is None:
            specificMenu.show()
            self.currentMenu = specificMenu
        else:
            self.startSectionInternal(index, data)

    def sectionSpecificMenuDone(self, menu, sectionIndex, data):
        menu.hide()
        self.startSectionInternal(sectionIndex, data)

    def startSectionInternal(self, index, data):
        if self.currentSectionObject is not None:
            self.currentSectionObject.destroy()

        self.mainMenuPanel.hide()
        self.mainMenuBackdrop.hide()
        self.currentMenu = None

        self.currentSectionIndex = index
        self.currentSectionData = data

        sectionModule = self.sections[index][0]

        if hasattr(sectionModule, "initialise"):
            initialisationMethod = sectionModule.initialise
        elif hasattr(sectionModule, "initialize"):
            initialisationMethod = sectionModule.initialize

        self.currentSectionObject = initialisationMethod(data)

    def selectSection(self):
        self.sectionMenu.show()
        self.currentMenu = self.sectionMenu

    def restartCurrentSection(self):
        self.gameOverScreen.hide()
        self.startSectionInternal(self.currentSectionIndex, self.currentSectionData)

    def gameOver(self):
        if self.currentSectionObject is not None:
            self.currentSectionObject.destroy()
            self.currentSectionObject = None

        if self.gameOverScreen.isHidden():
            self.gameOverScreen.show()

    def closeOptionsMenu(self):
        self.writeOptions()
        self.closeCurrentMenu()

    def closeCurrentMenu(self):
        if self.currentMenu is not None:
            self.currentMenu.hide()
            if self.currentMenu.hasPythonTag(TAG_PREVIOUS_MENU):
                otherMenu = self.currentMenu.getPythonTag(TAG_PREVIOUS_MENU)
                otherMenu.show()
                self.currentMenu = otherMenu
            else:
                self.currentMenu = None

    def destroy(self):
        self.shipSelectionMenu.clearPythonTag(TAG_PREVIOUS_MENU)

        for section in common.optionWidgets.values():
            for key, widgetList in section.items():
                for widget in widgetList[1:]:
                    if "extraArgs" in [optTuple[0] for optTuple in widget.options()]:
                        widget["extraArgs"] = []
        common.options = {}
        common.optionWidgets = {}
        common.optionCallbacks = {}

    def quit(self):
        self.destroy()

        common.base.userExit()

game = Game()
common.base.run()
