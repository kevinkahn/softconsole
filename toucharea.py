import config
import utilities
from config import debugprint
from logsupport import Info, Warning, Error


def InBut(pos, Key):
    return (pos[0] > Key.Center[0] - Key.Size[0]/2) and (pos[0] < Key.Center[0] + Key.Size[0]/2) and \
           (pos[1] > Key.Center[1] - Key.Size[1]/2) and (pos[1] < Key.Center[1] + Key.Size[1]/2)


class TouchPoint:
    def __init__(self, c, s):
        self.Center = c
        self.Size = s

class ManualKeyDesc(TouchPoint):
    def __init__(self, *args, **kwargs):
        # alternate creation signatures
        if len(args) == 2:
            # signature: ManualKeyDesc(keysection, keyname)
            # initialize by reading config file
            self.dosectioninit(*args)
        else:
            # signature: ManualKeyDesc(keyname, label, bcolor, charcoloron, charcoloroff, center=, size=, KOn=, KOff=, proc=)
            # initializing from program code case
            self.docodeinit(*args, **kwargs)

    def docodeinit(self, keyname, label, bcolor, charcoloron, charcoloroff, center=(0, 0), size=(0, 0), KOn='', KOff='',
                   proc=None):
        # NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
        # because of when config is imported and what walues are at that time versus at call time
        TouchPoint.__init__(self, center, size)
        self.name = keyname
        self.RealObj = proc
        self.KeyColor = bcolor
        self.KeyCharColorOn = charcoloron
        self.KeyCharColorOff = charcoloroff
        self.State = True
        self.label = label
        self.KeyOnOutlineColor = config.KeyOnOutlineColor if KOn == '' else KOn
        self.KeyOffOutlineColor = config.KeyOffOutlineColor if KOff == '' else KOff

    def dosectioninit(self, keysection, keyname):
        TouchPoint.__init__(self, (0, 0), (0, 0))
        utilities.LocalizeParams(self, keysection, 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
                                 'KeyCharColorOn', 'KeyCharColorOff', label=[keyname])
        self.name = keyname
        self.State = True
        self.RealObj = None  # this will get filled in by creator later - could be ISY node, ISY program, proc to call
