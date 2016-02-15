import pygame

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
    def __init__(self, keyname, label, center, size, bcolor, charcoloron, charcoloroff, KOn='', KOff=''):
        # NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
        TouchPoint.__init__(self, center, size)
        self.name = keyname
        self.backcolor = bcolor
        self.charcoloron = charcoloron
        self.charcoloroff = charcoloroff
        self.State = True
        self.label = utilities.normalize_label(label)
        self.KOnColor = config.KeyOnOutlineColor if KOn == '' else KOn
        self.KOffColor = config.KeyOffOutlineColor if KOff == '' else KOff

_p_SceneProxy = ''
_p_KeyRunThenName = ''
_p_type = 'ONOFF'

class KeyDesc(ManualKeyDesc):
    # Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU 

    def __init__(self, keysection, keyname):
        debugprint(config.dbgscreenbuild, "             New Key Desc ", keyname)
        ManualKeyDesc.__init__(self, keyname,
                               keysection.get("label", keyname),
                               (0, 0), (0, 0),
                               keysection.get("KeyColor", config.KeyColor),
                               keysection.get("KOnColor", config.KeyOnOutlineColor),
                               keysection.get("KOffColor", config.KeyOffOutlineColor))
        utilities.LocalizeParams(self, keysection)
        self.KeyRunThen = config.ISY.ProgramsByName[self.KeyRunThenName] if self.KeyRunThenName <> "" else None
        self.RealObj = None  # ISY Object corresponding to this key
        self.MonitorObj = None  # ISY Object monitored to reflect state in the key (generally a device within a Scene)

        # for ONOFF keys (and others later) map the real and monitored nodes in the ISY
        # map the key to a scene or device - prefer to map to a scene so check that first
        # Obj is the representation of the ISY Object itself, addr is the address of the ISY device/scene
        if self.type in ('ONOFF'):
            if keyname in config.ISY.ScenesByName:
                self.RealObj = config.ISY.ScenesByName[keyname]
                if self.SceneProxy <> '':
                    # explicit proxy assigned
                    if self.SceneProxy in config.ISY.NodesByAddr:
                        # address given
                        self.MonitorObj = config.ISY.NodesByAddr[self.SceneProxy]
                    elif self.SceneProxy in config.ISY.NodesByName:
                        self.MonitorObj = config.ISY.NodesByName[self.SceneProxy]
                    else:
                        config.Logs.Log('Bad explicit scene proxy:' + self.name, Warning)
                else:
                    for i in self.RealObj.members:
                        device = i[1]
                        if device.enabled:
                            self.MonitorObj = device
                            break
                        else:
                            config.Logs.Log('Skipping disabled device: ' + device.name, Warning)
                    if self.MonitorObj is None:
                        config.Logs.Log("No proxy for scene: " + keyname, Error)
                    debugprint(config.dbgscreenbuild, "Scene ", keyname, " default proxying with ",
                               self.MonitorObj.name)
            elif keyname in config.ISY.NodesByName:
                self.RealObj = config.ISY.NodesByName[keyname]
                self.MonitorObj = self.RealObj
            else:
                debugprint(config.dbgscreenbuild, "Screen", keyname, "unbound")
                config.Logs.Log('Key Binding missing: ' + self.name, Warning)
        elif self.type in ("ONBLINKRUNTHEN"):
            self.State = False
            if self.KeyRunThen is None:
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
            self.label) + "|Typ:" + self.type + "|Px:" + str(self.SceneProxy) + \
               "\n\r        |Ctr:" + str(self.Center) + "|Sz:" + str(self.Size)
