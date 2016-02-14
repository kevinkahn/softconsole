import webcolors

import displayscreen

wc = webcolors.name_to_rgb
import config
import time
import pygame
from config import debugprint, WAITEXIT
import screen

CharSize = [20]
Font = 'droidsansmono'


class ClockScreenDesc(screen.ScreenDesc):
    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "Build Clock Screen")
        screen.ScreenDesc.__init__(self, screensection, screenname, ())  # no extra cmd keys
        self.charcolor = screensection.get("CharColor", config.CharColor)
        self.lineformat = screensection.get("OutFormat", "")
        self.clockfont = screensection.get("Font", Font)
        self.fontsize = screensection.get("CharSize", CharSize)
        print self.fontsize
        for i in range(len(self.fontsize), len(self.lineformat)):
            print i
            self.fontsize.append(self.fontsize[-1])
            print self.fontsize

    def __repr__(self):
        return screen.ScreenDesc.__repr__(self) + "\r\n     ClockScreenDesc:" + str(self.charcolor) + ":" + str(
            self.lineformat) + ":" + str(self.fontsize)

    def HandleScreen(self, newscr=True):

        # stop any watching for device stream
        config.toDaemon.put([])

        config.screen.fill(wc(self.backcolor))

        def repaintClock(cycle):
            # param ignored for clock
            usefulheight = config.screenheight - config.topborder - config.botborder
            h = 0
            l = []

            for i in range(len(self.lineformat)):
                l.append(
                    config.fonts.Font(int(self.fontsize[i]), self.clockfont).render(time.strftime(self.lineformat[i]),
                                                                                    0, wc(self.charcolor)))
                h = h + l[i].get_height()
            s = (usefulheight - h)/(len(l) - 1)

            config.screen.fill(wc(self.backcolor),
                               pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
            vert_off = config.topborder + s
            for i in range(len(l)):
                horiz_off = (config.screenwidth - l[i].get_width())/2
                config.screen.blit(l[i], (horiz_off, vert_off))
                vert_off = vert_off + s + l[i].get_height()/2
            pygame.display.update()

        repaintClock(0)
        config.DS.draw_cmd_buttons(config.screen, self)

        while 1:
            choice = config.DS.NewWaitPress(self, callbackproc=repaintClock, callbackint=1)
            if choice[0] == WAITEXIT:
                return choice[1]


config.screentypes["Clock"] = ClockScreenDesc
