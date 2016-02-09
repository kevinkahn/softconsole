import pygame
import webcolors
import config
wc = webcolors.name_to_rgb
import time
import os

Info = 0
Warning = 1
Error = 2
    
class Logs():
    

    livelog = True
    livelogpos = 0
    log = []

    LogColors = ("white","yellow","red")

    def __init__(self, screen, dirnm):
        self.screen = screen
        self.LogFont = pygame.font.SysFont(None,23,False,False)
        self.logfilename = dirnm + '/' + time.strftime("%Y-%b-%d-%H-%M-%S-Log.txt")
        self.disklogfile = open(self.logfilename, "w")
        
    def Log(self, entry, severity=Info):
        self.log.append((severity, entry))
        self.disklogfile.write(time.strftime('%H:%M:%S') + ' Sev: ' + str(severity) +" "+ entry.encode('ascii',errors='backslashreplace') + '\n')
        self.disklogfile.flush()
        os.fsync(self.disklogfile)
        if self.livelog:
            if self.livelogpos == 0:
                config.screen.fill(wc('royalblue'))
            l = self.LogFont.render(entry,False,wc(self.LogColors[severity]))
            self.screen.blit(l,(10,self.livelogpos))
            pygame.display.update()
            self.livelogpos += self.LogFont.get_linesize()
            if self.livelogpos > config.screenheight - config.botborder:
                time.sleep(2)
                self.livelogpos = 0
            pygame.display.update()
            
    def RenderLog(self, backcolor, start=0):
        pos = 0
        config.screen.fill(wc(backcolor))
        for i in range(start,len(self.log)):
            l = self.LogFont.render(self.log[i][1],False,wc(self.LogColors[self.log[i][0]]))
            self.screen.blit(l,(10,pos))
            pos += self.LogFont.get_linesize()
            if pos > config.screenheight - config.botborder:
                pygame.display.update()
                return i+1
        pygame.display.update()
        return -1
            
        
