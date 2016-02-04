import webcolors
import pygame
wc = webcolors.name_to_rgb

Info = 0
Warning = 1
Error = 2
    
class Logs():
    

    livelog = True
    livelogpos = 0
    log = []

    LogColors = ("white","yellow","red")
    
    def __init__(self, screen):
        self.screen = screen
        self.LogFont = pygame.font.SysFont(None,20,False,False)
        
    def Log(self, entry, severity=Info):
        self.log.append((severity, entry))
        if self.livelog:
            l = self.LogFont.render(entry,False,wc(self.LogColors[severity]))
            self.screen.blit(l,(10,self.livelogpos))
            pygame.display.update()
            self.livelogpos += self.LogFont.get_linesize()
            pygame.display.update()
        