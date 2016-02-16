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
    #   def __init__(self, keyname, label, center, size, bcolor, charcoloron, charcoloroff, KOn='', KOff=''):
    def docodeinit(self, keyname, label, center, size, bcolor, charcoloron, charcoloroff, KOn='', KOff=''):
        # NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
        # because of when config is imported and what walues are at that time versus at call time
        TouchPoint.__init__(self, center, size)
        self.name = keyname
        self.KeyColor = bcolor
        self.KeyCharColorOn = charcoloron
        self.KeyCharColorOff = charcoloroff
        self.State = True
        self.label = utilities.normalize_label(label)
        self.KeyOnOutlineColor = config.KeyOnOutlineColor if KOn == '' else KOn
        self.KeyOffOutlineColor = config.KeyOffOutlineColor if KOff == '' else KOff

    def dosectioninit(self, keysection, keyname):
        TouchPoint.__init__(self, (0, 0), (0, 0))
        utilities.LocalizeParams(self, keysection, 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
                                 'KeyCharColorOn', 'KeyCharColorOff')
        self.name = keyname
        self.State = True
        self.label = utilities.normalize_label(self.label if self.label <> [] else keyname)

    def __init__(self, *args, **kwargs):

        if len(args) == 2:
            self.dosectioninit(*args)
        else:
            # signature: ManualKeyDesc(keyname, label, center, size, bcolor, charcoloron, charcoloroff, KOn='', KOff='')
            # initializing from program code case
            self.docodeinit(*args, **kwargs)
