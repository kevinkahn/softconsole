import ISYSetup
import DisplayScreen
import webcolors
import config
import functools
import time
import pygame
from config import debugprint, WAITEXIT
wc = webcolors.name_to_rgb
import Screen


class ClockScreenDesc(Screen.ScreenDesc):

    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "Build Clock Screen")
        Screen.ScreenDesc.__init__(self, screensection, screenname, 0) # no extra cmd keys
        self.charcolor    = screensection.get("CharColor",config.CharColor)
        self.lineformat   = screensection.get("OutFormat","")
        self.fontsize     = int(screensection.get("CharSize",config.CharSize))
        self.ClkFont      = pygame.font.SysFont(None,self.fontsize,True,True)
        
    def __repr__(self):
        return Screen.ScreenDesc.__repr__(self)+"\r\n     ClockScreenDesc:"+str(self.charcolor)+":"+str(self.lineformat)+":"+str(self.fontsize)

    def HandleScreen(self,newscr=True):
    
        # stop any watching for device stream
        config.toDaemon.put([])
         
        config.screen.screen.fill(wc(self.backcolor))

        def repaintClock(cycle):
            # param ignored for clock
            usefulheight = config.screenheight - config.topborder - config.botborder
            h = 0
            l = []
            
            for i in range(len(self.lineformat)):
                l.append(self.ClkFont.render(time.strftime(self.lineformat[i]), 0, wc(self.charcolor)))
                h = h + l[i].get_height()
            s = (usefulheight - h)/len(l)
        
            config.screen.screen.fill(wc(self.backcolor),pygame.Rect(0,0,config.screenwidth,config.screenheight-config.botborder))
            for i in range(len(l)):
                vert_off = config.topborder + (i+1)*s + l[i].get_height()/2
                horiz_off = (config.screenwidth - l[i].get_width())/2
                config.screen.screen.blit(l[i],(horiz_off, vert_off))
            pygame.display.update()
            
        repaintClock(0)
        DisplayScreen.draw_cmd_buttons(config.screen,self)
        
        while 1:
            choice = config.screen.NewWaitPress(self, callbackproc=repaintClock, callbackint=1)
            if choice[0] ==  WAITEXIT:
                return  choice[1]
        
config.screentypes["Clock"] = ClockScreenDesc