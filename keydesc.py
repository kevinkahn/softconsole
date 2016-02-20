import config
import utilities
import toucharea
from config import debugprint
from logsupport import Info, Warning, Error


class KeyDesc(toucharea.ManualKeyDesc):
    # Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU

    def __init__(self, keysection, keyname):
        debugprint(config.dbgscreenbuild, "             New Key Desc ", keyname)
        toucharea.ManualKeyDesc.__init__(self, keysection, keyname)
        utilities.LocalizeParams(self, keysection, SceneProxy='', KeyRunThenName='', type='ONOFF')
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
                        config.Logs.Log('Bad explicit scene proxy:' + self.name, severity=Warning)
                else:
                    for i in self.RealObj.members:
                        device = i[1]
                        if device.enabled and device.hasstatus:
                            self.MonitorObj = device
                            break
                        else:
                            config.Logs.Log('Skipping disabled/nonstatus device: ' + device.name, severity=Warning)
                    if self.MonitorObj is None:
                        config.Logs.Log("No proxy for scene: " + keyname, severity=Error)
                    debugprint(config.dbgscreenbuild, "Scene ", keyname, " default proxying with ",
                               self.MonitorObj.name)
            elif keyname in config.ISY.NodesByName:
                self.RealObj = config.ISY.NodesByName[keyname]
                self.MonitorObj = self.RealObj
            else:
                debugprint(config.dbgscreenbuild, "Screen", keyname, "unbound")
                config.Logs.Log('Key Binding missing: ' + self.name, severity=Warning)
        elif self.type in ("ONBLINKRUNTHEN"):
            self.State = False
            self.RealObj = config.ISY.ProgramsByName[self.KeyRunThenName] if self.KeyRunThenName <> "" else None
            if self.RealObj is None:
                debugprint(config.dbgscreenbuild, "Unbound program key: ", self.label)
                config.Logs.Log("Missing Prog binding: " + self.name, severity=Warning)
        else:
            debugprint(config.dbgscreenbuild, "Unknown key type: ", self.label)
            config.Logs.Log("Bad keytype: " + self.name, severity=Warning)
        debugprint(config.dbgscreenbuild, repr(self))

    def __repr__(self):
        return "KeyDesc:" + self.name + "|ST:" + str(self.State) + "|Clr:" + str(self.KeyColor) + "|OnC:" + str(
            self.KeyCharColorOn) + "|OffC:" \
               + str(self.KeyCharColorOff) + "\n\r        |Lab:" + str(
            self.label) + "|Typ:" + self.type + "|Px:" + str(self.SceneProxy) + \
               "\n\r        |Ctr:" + str(self.Center) + "|Sz:" + str(self.Size)
