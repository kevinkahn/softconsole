import pygame
import webcolors

import config

wc = webcolors.name_to_rgb
import time
import os

Info = 0
Warning = 1
Error = 2


class Logs:
    livelog = True
    livelogpos = 0
    log = []

    LogColors = ("white", "yellow", "red")

    def __init__(self, screen, dirnm):
        self.screen = screen
        self.logfontsize = 23
        os.chdir(dirnm)
        q = [k for k in os.listdir('.') if 'Console.log' in k]
        if "Console.log." + str(config.maxlog) in q:
            os.remove('Console.log.' + str(config.maxlog))
        for i in range(config.maxlog - 1, 0, -1):
            if "Console.log." + str(i) in q:
                os.rename('Console.log.' + str(i), "Console.log." + str(i + 1))
        os.rename('Console.log', 'Console.log.1')
        self.disklogfile = open('Console.log', 'w')
        os.chmod('Console.log', 0o555)

    def Log(self, entry, severity=Info, diskonly=False):
        """

        :param severity:
        :param entry:
        """
        if not diskonly:
            self.log.append((severity, entry))
        self.disklogfile.write(time.strftime('%H:%M:%S')
                               + ' Sev: ' + str(severity) + " " + entry.encode('ascii',
                                                                               errors='backslashreplace') + '\n')
        self.disklogfile.flush()
        os.fsync(self.disklogfile.fileno())
        if self.livelog and not diskonly:
            if self.livelogpos == 0:
                config.screen.fill(wc('royalblue'))
            l = config.fonts.Font(self.logfontsize).render(entry, False, wc(self.LogColors[severity]))
            self.screen.blit(l, (10, self.livelogpos))
            pygame.display.update()
            self.livelogpos += config.fonts.Font(self.logfontsize).get_linesize()
            if self.livelogpos > config.screenheight - config.botborder:
                time.sleep(2)
                self.livelogpos = 0
            pygame.display.update()

    def RenderLog(self, backcolor, start=0):
        pos = 0
        config.screen.fill(wc(backcolor))
        for i in range(start, len(self.log)):
            l = config.fonts.Font(self.logfontsize).render(self.log[i][1], False, wc(self.LogColors[self.log[i][0]]))
            self.screen.blit(l, (10, pos))
            pos += config.fonts.Font(self.logfontsize).get_linesize()
            if pos > config.screenheight - config.botborder:
                pygame.display.update()
                return i + 1
        pygame.display.update()
        return -1
