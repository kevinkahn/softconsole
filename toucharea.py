import pygame

import config
from config import debugprint
from logsupport import Info, Warning, Error


def InBut(pos, Key):
    return (pos[0] > Key.Center[0] - Key.Size[0]/2) and (pos[0] < Key.Center[0] + Key.Size[0]/2) and \
           (pos[1] > Key.Center[1] - Key.Size[1]/2) and (pos[1] < Key.Center[1] + Key.Size[1]/2)


ButtonFontSizes = (30, 25, 23, 21, 19)
ButtonFonts = []


def InitButtonFonts():
    for i in ButtonFontSizes:
        ButtonFonts.append(pygame.font.SysFont("", i))


class TouchPoint:
    def __init__(self, c, s):
        self.Center = c
        self.Size = s


class ManualKeyDesc(TouchPoint):
    def __init__(self, keyname, label, center, size, bcolor, charcoloron, charcoloroff,
                 KOn=config.DefaultKeyOnOutlineColor, KOff=config.DefaultKeyOffOutlineColor):
        TouchPoint.__init__(self, center, size)
        self.name = keyname
        self.backcolor = bcolor
        self.charcoloron = charcoloron
        self.charcoloroff = charcoloroff
        self.State = True
        self.label = label if not isinstance(label, basestring) else [label]
        self.KOnColor = KOn
        self.KOffColor = KOff


class KeyDesc(ManualKeyDesc):
    # Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU 

    def __init__(self, keysection, keyname):
        debugprint(config.dbgscreenbuild, "             New Key Desc ", keyname)
        ManualKeyDesc.__init__(self, keyname,
                               keysection.get("label", keyname),
                               (0, 0), (0, 0),
                               keysection.get("Kcolor", config.DefaultKeyColor),
                               keysection.get("KOnColor", config.DefaultKeyOnOutlineColor),
                               keysection.get("KOffColor", config.DefaultKeyOffOutlineColor))

        self.typ = keysection.get("Ktype", "ONOFF")
        rt = keysection.get("Krunthen", "")
        self.Krunthen = config.ISY.ProgramsByName[rt] if rt <> "" else None
        self.sceneproxy = keysection.get("sceneproxy", "")
        self.RealObj = None  # ISY Object corresponding to this key
        self.MonitorObj = None  # ISY Object monitored to reflect state in the key (generally a device within a Scene)

        # for ONOFF keys (and others later) map the real and monitored nodes in the ISY
        # map the key to a scene or device - prefer to map to a scene so check that first
        # Obj is the representation of the ISY Object itself, addr is the address of the ISY device/scene
        if self.typ in ('ONOFF'):
            if keyname in config.ISY.ScenesByName:
                self.RealObj = config.ISY.ScenesByName[keyname]
                if self.sceneproxy <> '':
                    # explicit proxy assigned
                    if self.sceneproxy in config.ISY.NodesByAddr:
                        # address given
                        self.MonitorObj = config.ISY.NodesByAddr[self.sceneproxy]
                    elif self.sceneproxy in config.ISY.NodesByName:
                        self.MonitorObj = config.ISY.NodesByName[self.sceneproxy]
                    else:
                        config.Logs.Log('Bad explicit scene proxy:' + self.name, Warning)
                else:
                    self.MonitorObj = self.RealObj.members[0][1]
                    debugprint(config.dbgscreenbuild, "Scene ", keyname, " default proxying with ",
                               self.MonitorObj.name)
            elif keyname in config.ISY.NodesByName:
                self.RealObj = config.ISY.NodesByName[keyname]
                self.MonitorObj = self.RealObj
            else:
                debugprint(config.dbgscreenbuild, "Screen", keyname, "unbound")
                config.Logs.Log('Key Binding missing: ' + self.name, Warning)
        elif self.typ in ("ONBLINKRUNTHEN"):
            self.State = False
            if self.Krunthen is None:
                debugprint(config.dbgscreenbuild, "Unbound program key: ", self.label)
                config.Logs.Log("Missing Prog binding: " + self.name, Warning)
        else:
            debugprint(config.dbgscreenbuild, "Unknown key type: ", self.label)
            config.Logs.Log("Bad keytype: " + self.name, Warning)
        debugprint(config.dbgscreenbuild, repr(self))

    def __repr__(self):
        return "KeyDesc:" + self.name + "|ST:" + str(self.State) + "|Clr:" + str(self.backcolor) + "|OnC:" + str(
            self.charcoloron) + "|OffC:" \
               + str(self.charcoloroff) + "\n\r        |Lab:" + str(
            self.label) + "|Typ:" + self.typ + "|Px:" + str(self.sceneproxy) + \
               "\n\r        |Ctr:" + str(self.Center) + "|Sz:" + str(self.Size)
