import pygame
import config


class Fonts(object):
    def __init__(self):
        pygame.font.init()
        self.fontcache = {}  # cache is tree dir with first key as name, second as size, third as ital, fourth as bold

    def Font(self, size, face="", bold=False, italic=False):
        def gennewfont():
            return pygame.font.SysFont(name, size, bold, italic)

        try:
            return self.fontcache[face][size][italic][bold]
        except KeyError:
            name = face if face <> "" else None
            if face not in self.fontcache:
                self.fontcache[face] = {size: {italic: {bold: gennewfont()}}}
            else:
                if size not in self.fontcache[face]:
                    self.fontcache[face][size] = {italic: {bold: gennewfont()}}
                else:
                    if italic not in self.fontcache[face][size]:
                        self.fontcache[face][size][italic] = {bold: gennewfont()}
                    else:
                        if bold not in self.fontcache[face][size][italic]:
                            self.fontcache[face][size][italic][bold] = gennewfont()
                        else:
                            pass  # log this - should never get here
            config.Logs.Log('New font: ', face if face <> "" else '-Sys-', ' :', size, (' b', ' B')[bold],
                            (' i', ' I')[italic],
                            diskonly=True)
            return self.fontcache[face][size][italic][bold]
