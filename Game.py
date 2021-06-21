
from direct.showbase.ShowBase import ShowBase

from panda3d.core import WindowProperties, TextNode, Vec4
from direct.gui.DirectGui import *

import Section2.Section2 as Section1
import Section2.Section2 as Section2
import Section3.Section3 as Section3
import Section2.Section2 as Section4

from Ships import shipSpecs

class Game(ShowBase):
    @staticmethod
    def makeButton(text, command, menu, width, extraArgs = None):
        btn = DirectButton(text = text,
                           command = command,
                           scale = 0.1,
                           parent = menu,
                           text_align = TextNode.ALeft,
                           frameSize = (-0.1, width, -0.75, 0.75),
                           text_pos = (0, -0.375)
                           )
        if extraArgs is not None:
            btn["extraArgs"] = extraArgs
        return btn

    def __init__(self):
        ShowBase.__init__(self)

        properties = WindowProperties()
        properties.setSize(1280, 720)
        self.win.requestProperties(properties)

        self.win.setClearColor(Vec4(0, 0, 0, 1))

        self.disableMouse()

        self.exitFunc = self.cleanup

        self.accept("window-event", self.windowUpdated)

        ### Main Menu

        self.mainMenuBackdrop = DirectFrame(
                                            frameSize = (-1/self.aspect2d.getSx(), 1/self.aspect2d.getSx(), -1, 1),
                                           )

        self.title = DirectLabel(text = "CAPTAIN PANDA",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.07,
                                 pos = (0, 0, 0.9),
                                 text_align = TextNode.ALeft)
        self.title = DirectLabel(text = "and the",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.05,
                                 pos = (0, 0, 0.85),
                                 text_align = TextNode.ALeft)
        self.title = DirectLabel(text = "INVASION OF THE MECHANOIDS!",
                                 parent = self.mainMenuBackdrop,
                                 scale = 0.1,
                                 pos = (0, 0, 0.7625),
                                 text_align = TextNode.ALeft)

        self.mainMenuPanel = DirectFrame(
                                    frameSize = (0, 1.25, -1, 1),
                                    frameColor = (0, 0, 0, 0.5)
                                   )

        buttons = []

        btn = Game.makeButton("New Game", self.startGame, self.mainMenuPanel, 10)
        buttons.append(btn)

        btn = Game.makeButton("Chapter Selection", self.selectSection, self.mainMenuPanel, 10)
        buttons.append(btn)

        btn = Game.makeButton("Options", self.openOptions, self.mainMenuPanel, 10)
        buttons.append(btn)

        btn = Game.makeButton("Quit", self.quit, self.mainMenuPanel, 10)
        buttons.append(btn)

        buttonSpacing = 0.2
        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing

        ### Options Menu

        ### Section Menu

        self.sectionMenu = DirectDialog(
                                        frameSize = (0, 2, -0.85, 0.85),
                                        fadeScreen = 0.5,
                                        pos = (0, 0, 0),
                                        relief = DGG.FLAT
                                       )
        self.sectionMenu.hide()

        buttons = []

        btn = Game.makeButton("Chapter 1 // A Warrior's Choice", self.startSection, self.sectionMenu, 15, extraArgs = [0])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 2 // Across the Night", self.startSection, self.sectionMenu, 15, extraArgs = [1])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 3 // Facing the Foe", self.startSection, self.sectionMenu, 15, extraArgs = [2])
        buttons.append(btn)

        btn = Game.makeButton("Chapter 4 // The Escape", self.startSection, self.sectionMenu, 15, extraArgs = [3])
        buttons.append(btn)

        buttonSpacing = 0.3
        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing


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
                                              frameSize = (0, 2, -0.7, 0.7),
                                              fadeScreen = 0.5,
                                              relief = DGG.FLAT
                                             )
        self.shipSelectionMenu.hide()

        label = DirectLabel(text = "Select a Ship:",
                            parent = self.shipSelectionMenu,
                            scale = 0.1,
                            pos = (0.085, 0, 0.5),
                            text_align = TextNode.ALeft)

        btn = Game.makeButton("Light fighter", self.sectionSpecificMenuDone, self.shipSelectionMenu, 15,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[0]])
        buttons.append(btn)

        btn = Game.makeButton("Medium Interceptor", self.sectionSpecificMenuDone, self.shipSelectionMenu, 15,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[1]])
        buttons.append(btn)

        btn = Game.makeButton("Heavy Bombardment Platform", self.sectionSpecificMenuDone, self.shipSelectionMenu, 15,
                              extraArgs = [self.shipSelectionMenu, 1, shipSpecs[2]])
        buttons.append(btn)

        buttonY = (len(buttons) - 1)*0.5*buttonSpacing
        for btn in buttons:
            btn.setPos(0.1, 0, buttonY)
            buttonY -= buttonSpacing

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

        self.accept("f", self.toggleFrameRateMeter)
        self.showFrameRateMeter = False

    def toggleFrameRateMeter(self):
        self.showFrameRateMeter = not self.showFrameRateMeter

        self.setFrameRateMeter(self.showFrameRateMeter)

    def windowUpdated(self, window):
        ShowBase.windowEvent(self, window)
        self.mainMenuBackdrop["frameSize"] = (-1/self.aspect2d.getSx(), 1/self.aspect2d.getSx(),
                                              -1/self.aspect2d.getSz(), 1/self.aspect2d.getSz())
        self.mainMenuPanel.setX(self.render2d, -1)
        self.mainMenuPanel["frameSize"] = (0, 1.25, -1/self.aspect2d.getSz(), 1/self.aspect2d.getSz())
        self.sectionMenu.setPos(self.render, -0.8, 0, 0)
        self.shipSelectionMenu.setPos(self.render, -0.6, 0, 0)

    def openMenu(self):
        self.currentSectionIndex = 0
        self.currentSectionData = None

        self.gameOverScreen.hide()
        self.mainMenuBackdrop.show()
        self.mainMenuPanel.show()

    def openOptions(self):
        pass

    def startGame(self):
        self.startSection(0)

    def startSection(self, index, data = None):
        self.sectionMenu.hide()

        specificMenu = self.sections[index][1]
        if specificMenu is not None and data is None:
            specificMenu.show()
        else:
            self.startSectionInternal(index, data)

    def sectionSpecificMenuDone(self, menu, sectionIndex, data):
        menu.hide()
        self.startSectionInternal(sectionIndex, data)

    def startSectionInternal(self, index, data):
        if self.currentSectionObject is not None:
            self.currentSectionObject.cleanup()

        self.mainMenuPanel.hide()
        self.mainMenuBackdrop.hide()

        self.currentSectionIndex = index
        self.currentSectionData = data

        sectionModule = self.sections[index][0]

        if hasattr(sectionModule, "initialise"):
            initialisationMethod = sectionModule.initialise
        elif hasattr(sectionModule, "initialize"):
            initialisationMethod = sectionModule.initialize

        self.currentSectionObject = initialisationMethod(self, data)

    def selectSection(self):
        self.sectionMenu.show()

    def restartCurrentSection(self):
        self.gameOverScreen.hide()
        self.startSectionInternal(self.currentSectionIndex, self.currentSectionData)

    def gameOver(self):
        if self.currentSectionObject is not None:
            self.currentSectionObject.cleanup()
            self.currentSectionObject = None

        if self.gameOverScreen.isHidden():
            self.gameOverScreen.show()

    def cleanup(self):
        pass

    def quit(self):
        self.cleanup()

        self.userExit()

game = Game()
game.run()