import config
import pygame
from config import debugprint, WAITNORMALBUTTON
import toucharea
import displayscreen
from displayscreen import draw_button
import webcolors
wc = webcolors.name_to_rgb
import logsupport
from logsupport import Logs
import time
import os, signal

def interval_str(sec_elapsed):
    d = int(sec_elapsed / (60 * 60 * 24))
    h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = int(sec_elapsed % 60)
    return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)

class MaintScreenDesc():

    def __init__(self):
        debugprint(config.dbgscreenbuild, "Build Maintenance Screen")

        self.charcolor      = "white"
        self.backcolor      = "royalblue"
        self.dimtimeout     = 100000 # infinite
        self.ExtraCmdKeys   = []     

        self.PrevScreenKey  = None
        self.NextScreenKay  = None
        self.ExtraCmdKeys   = []

        self.MaintFont      = pygame.font.SysFont(None,40,True,True)
        self.MaintFont2     = pygame.font.SysFont(None,25,True,True)

        self.name           = "Maint"
        self.label          = ["Maintenance"]
        
        maintkeys           = {'log':'Show Log','exit':'Exit Maintenance','shut':'Shutdown Console'}
        self.menukeysbyord      = []
        self.keysbyord = []
        t = config.topborder + 130
        for key in maintkeys:
            self.menukeysbyord.append(toucharea.ManualKeyDesc(key, maintkeys[key], (config.screenwidth/2, t),
                                                              (config.screenwidth-2*config.horizborder,70),'gold','black','black','black','black'))
            t += 80
        
        self.pagekeysbyord = [toucharea.TouchPoint((config.screenwidth/2, config.screenheight/2), (config.screenwidth, config.screenheight))]


    def ShowScreen(self):

        config.screen.fill(wc(self.backcolor))
        r = self.MaintFont.render("Console Maintenance", 0, wc(self.charcolor))
        rl = (config.screenwidth-r.get_width())/2
        config.screen.blit(r,(rl,config.topborder))
        r = self.MaintFont2.render("Up: " + interval_str(time.time() - config.starttime), 0, wc(self.charcolor))
        rl = (config.screenwidth-r.get_width())/2
        config.screen.blit(r,(rl,config.topborder+30))
        for K in self.keysbyord:
            draw_button(config.screen, K)
        pygame.display.update()

    def HandleScreen(self,newscr=True):
        config.toDaemon.put([])
        # stop any watching for device stream
        self.keysbyord = self.menukeysbyord
        Logs = config.Logs
        Logs.Log("Entering Maint Screen")
        self.ShowScreen()

        while 1:
            choice = config.DS.NewWaitPress(self)
            if choice[0] == WAITNORMALBUTTON:
                K = self.keysbyord[choice[1]]
                if K.name == 'exit':
                    return config.HomeScreen
                elif K.name == 'log':
                    item = 0
                    self.keysbyord = self.pagekeysbyord # make whole screen single invisible key
                    while item >= 0:
                        item = Logs.RenderLog(self.backcolor, start = item)
                        temp = config.DS.NewWaitPress(self)
                    self.keysbyord = self.menukeysbyord
                    self.ShowScreen()
                elif K.name == 'shut':
                    Logs.Log("Manual Shutdown Requested")
                    config.screen.fill(wc("red"))
                    r = self.MaintFont.render("Shutting Down",0,wc("white"))
                    config.screen.blit(r, ((config.screenwidth-r.get_width())/2, config.screenheight*.4))
                    pygame.display.update()
                    time.sleep(3)
                    os.kill(config.DaemonProcess.pid,signal.SIGTERM)
                else:
                    print "No match in maint"
                    
            else:
                return choice[1]
           
        
        
        

       