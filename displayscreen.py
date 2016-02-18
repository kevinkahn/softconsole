import time

import pygame
import webcolors
import hw

import config
import toucharea
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITEXIT, WAITISYCHANGE, WAITEXTRACONTROLBUTTON
from logsupport import Warning
from utilities import scaleW, scaleH

wc = webcolors.name_to_rgb

class DisplayScreen:

    def __init__(self):

        print "Screensize: ", config.screenwidth, config.screenheight
        config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
        config.Logs.Log(
            "Scaling ratio: " + "{0:.2f}".format(config.dispratioW) + ':' + "{0:.2f}".format(config.dispratioH))

        # define user events
        self.MAXTIMEHIT = pygame.event.Event(pygame.USEREVENT)
        self.INTERVALHIT = pygame.event.Event(pygame.USEREVENT + 1)
        self.GOHOMEHIT = pygame.event.Event(pygame.USEREVENT + 2)
        self.isDim = False
        self.presscount = 0
        self.AS = None
        self.BrightenToHome = False
        self.ButtonFontSizes = tuple(scaleH(i) for i in (31, 28, 25, 22, 20, 18, 16))  # todo pixel

    def draw_button(self, screen, Key, shrink=True, firstfont=0):
        lines = len(Key.label)
        buttonsmaller = (Key.Size[0] - scaleW(6), Key.Size[1] - scaleH(6))  # todo pixel
        x = Key.Center[0] - Key.Size[0]/2
        y = Key.Center[1] - Key.Size[1]/2

        HiColor = Key.KeyOnOutlineColor if Key.State else Key.KeyOffOutlineColor
        pygame.draw.rect(screen, wc(Key.KeyColor), ((x, y), Key.Size), 0)
        bord = 3  # todo pixel - probably should use same scaling in both dimensions since this is a line width
        pygame.draw.rect(screen, wc(HiColor), ((x + scaleW(bord), y + scaleH(bord)), buttonsmaller), bord)
        s = pygame.Surface(Key.Size)
        s.set_alpha(150)
        s.fill(wc("white"))

        if not Key.State:
            screen.blit(s, (x, y))
        # compute writeable area for text
        textarea = (buttonsmaller[0] - 2, buttonsmaller[1] - 2)  #todo pixel not scaled
        fontchoice = self.ButtonFontSizes[firstfont]
        if shrink:
            for l in range(lines):
                for i in range(firstfont, len(self.ButtonFontSizes) - 1):
                    txtsize = config.fonts.Font(self.ButtonFontSizes[i]).size(Key.label[l])
                    if lines*txtsize[1] >= textarea[1] or txtsize[0] >= textarea[0]:
                        fontchoice = self.ButtonFontSizes[i + 1]

        for i in range(lines):
            ren = config.fonts.Font(fontchoice).render(Key.label[i], 0, wc(HiColor))
            vert_off = ((i + 1)*Key.Size[1]/(1 + lines)) - ren.get_height()/2
            horiz_off = (Key.Size[0] - ren.get_width())/2
            screen.blit(ren, (x + horiz_off, y + vert_off))

        pygame.display.update()

    def draw_cmd_buttons(self, scr, AS):
        if not self.BrightenToHome:  # suppress command buttons on sleep screen when any touch witll brighten/gohome
            self.draw_button(scr, AS.PrevScreenKey)
            self.draw_button(scr, AS.NextScreenKey)
            for K in AS.ExtraCmdKeys:
                self.draw_button(scr, K)

    def GoDim(self, dim):
        if dim:
            hw.GoDim()
            self.isDim = True
            if self.AS == config.HomeScreen:
                self.BrightenToHome = True
                return config.DimHomeScreenCover
        else:
            hw.GoBright()
            self.isDim = False
            if self.BrightenToHome:
                self.BrightenToHome = False
                return config.HomeScreen

    def NewWaitPress(self, ActiveScreen, callbackint=0, callbackproc=None, callbackcount=0):

        self.AS = ActiveScreen
        if callbackint <> 0:
            pygame.time.set_timer(self.INTERVALHIT.type, int(callbackint*1000))
        cycle = callbackcount if callbackcount <> 0 else 100000000  # essentially infinite
        if self.isDim and self.AS == config.DimHomeScreenCover:
            pygame.time.set_timer(self.GOHOMEHIT.type, 0)  # in final quiet state so cancel gohome until a touch
        else:
            pygame.time.set_timer(self.MAXTIMEHIT.type,
                                  self.AS.DimTO*1000)  # if not in final quiet state set dim timer

        while True:
            rtn = (0, 0)
            if not config.fromDaemon.empty():
                item = config.fromDaemon.get()
                debugprint(config.dbgMain, time.time(), "ISY reports change: ", "Key: ", str(item))
                if item[0] == "Log":
                    config.Logs.Log(item[1], severity=item[2])
                    continue
                elif item[0] == "Node":
                    rtn = (WAITISYCHANGE, (item[1], item[2]))
                    break
                else:
                    config.Logs.Log("Bad msg from watcher: " + str(item), Severity=Warning)
            event = pygame.fastevent.poll()

            if event.type == pygame.NOEVENT:
                time.sleep(.01)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
                if self.presscount < 10:  # this is debug code for a weird/unreproducible RPi behavior where touch is off
                    print pos
                    self.presscount += 1
                tapcount = 1
                pygame.time.delay(config.MultiTapTime)
                while True:
                    eventx = pygame.fastevent.poll()
                    if eventx.type == pygame.NOEVENT:
                        break
                    elif eventx.type == pygame.MOUSEBUTTONDOWN:
                        tapcount += 1
                        pygame.time.delay(config.MultiTapTime)
                    else:
                        continue
                if tapcount > 2:
                    self.GoDim(False)
                    rtn = (WAITEXIT, tapcount)
                    break
                # on any touch reset return to home screen
                pygame.time.set_timer(self.GOHOMEHIT.type, int(config.HomeScreenTO)*1000)
                # on any touch restart dim timer and reset to bright if dim
                pygame.time.set_timer(self.MAXTIMEHIT.type, self.AS.DimTO*1000)
                dimscr = self.GoDim(False)
                if dimscr is not None:
                    rtn = (WAITEXIT, config.HomeScreen)
                    break

                for i in range(len(self.AS.keysbyord)):
                    K = self.AS.keysbyord[i]
                    if toucharea.InBut(pos, K):
                        if tapcount == 1:
                            rtn = (WAITNORMALBUTTON, i)
                        else:
                            rtn = (WAITNORMALBUTTONFAST, i)
                if self.AS.PrevScreenKey is not None:
                    if toucharea.InBut(pos, self.AS.PrevScreenKey):
                        rtn = (WAITEXIT, self.AS.PrevScreen)
                    elif toucharea.InBut(pos, self.AS.NextScreenKey):
                        rtn = (WAITEXIT, self.AS.NextScreen)
                for K in self.AS.ExtraCmdKeys:
                    if toucharea.InBut(pos, K):
                        rtn = (WAITEXTRACONTROLBUTTON, K.name)
                if rtn[0] <> 0:
                    break

            elif event.type == self.MAXTIMEHIT.type:
                dimscr = self.GoDim(True)
                if dimscr is not None:
                    rtn = (WAITEXIT, dimscr)
                    break
            elif event.type == self.INTERVALHIT.type:
                if (callbackproc is not None) and (cycle > 0):
                    callbackproc(cycle)
                    cycle -= 1
            elif event.type == self.GOHOMEHIT.type:
                rtn = (WAITEXIT, config.HomeScreen)
                break
            else:
                pass  # ignore and flush other events

        pygame.time.set_timer(self.INTERVALHIT.type, 0)
        pygame.time.set_timer(self.MAXTIMEHIT.type, 0)

        return rtn
