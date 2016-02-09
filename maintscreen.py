import config
import pygame
from config import debugprint, WAITNORMALBUTTON
import toucharea
import subprocess
from displayscreen import draw_button
import webcolors
wc = webcolors.name_to_rgb
from logsupport import Logs, Info, Warning, Error
import time
import sys

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
        
        maintkeys           = ('log','exit','shut','shutpi','reboot')
        mainttitles         = ('Show Log','Exit Maintenance','Shutdown Console','Shutdown Pi','Reboot Pi')
        self.menukeysbyord      = []
        self.keysbyord = []
        t = config.topborder + 100
        for i in range(len(maintkeys)):
            self.menukeysbyord.append(toucharea.ManualKeyDesc(maintkeys[i], mainttitles[i], (config.screenwidth/2, t),
                                                              (config.screenwidth-2*config.horizborder,65),'gold','black','black','black','black'))
            t += 70
        
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
                    self.Exit_Options("Manual Shutdown Requested", "Shutting Down")
                    sys.exit()
                elif K.name == 'shutpi':
                    self.Exit_Options("Shutdown Pi Requested","Shutting Down Pi")
                    subprocess.Popen('sudo shutdown -P now', shell=True)
                    sys.exit()
                elif K.name == 'reboot':
                    self.Exit_Options("Reboot Pi Requested","Rebooting Pi")
                    subprocess.Popen('sudo reboot', shell=True)
                    sys.exit()
                else:
                    Logs.Log("Internal Error",Error)
                    
            else:
                return choice[1]

    def Exit_Options(self, msg,scrnmsg):
        config.Logs.Log(msg)
        config.screen.fill(wc("red"))
        r = self.MaintFont.render(scrnmsg, 0, wc("white"))
        config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
        pygame.display.update()
        time.sleep(2)
           
        
        
        

       
