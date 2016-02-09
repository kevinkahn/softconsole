import isysetup
import config
import pygame
from config import debugprint
import screen

def InBut(pos,Key):
    return (pos[0] > Key.Center[0] - Key.Size[0]/2) and (pos[0] < Key.Center[0] + Key.Size[0]/2) and \
           (pos[1] > Key.Center[1] - Key.Size[1]/2) and (pos[1] < Key.Center[1] + Key.Size[1]/2)

ButtonFontSizes = (30,25,23,21,19)
ButtonFonts = []

def InitButtonFonts():
    for i in ButtonFontSizes:
        ButtonFonts.append(pygame.font.SysFont("",i))
        

class TouchPoint:
    def __init__(self,c,s):
        self.Center       = c
        self.Size         = s

class ManualKeyDesc(TouchPoint):
    def __init__(self, keyname, label, center, size, bcolor, charcoloron, charcoloroff, KOn=config.DefaultKeyOnOutlineColor, KOff=config.DefaultKeyOffOutlineColor):
        TouchPoint.__init__(self,center,size)
        self.name = keyname
        self.backcolor = bcolor
        self.charcoloron = charcoloron
        self.charcoloroff = charcoloroff
        self.State        = True
        self.label =  label if not isinstance(label, basestring) else [label]
        self.KOnColor = KOn
        self.KOffColor = KOff        
        
class KeyDesc(ManualKeyDesc):
    # Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU 
    
    def __init__(self, keysection, keyname):
        debugprint(config.dbgscreenbuild, "             New Key Desc ", keyname)

        ManualKeyDesc.__init__(self, keyname,
                               keysection.get("label",keyname),
                               (0,0), (0,0),
                               keysection.get("Kcolor", config.DefaultKeyColor),
                               keysection.get("KOnColor", config.DefaultKeyOnOutlineColor),
                               keysection.get("KOffColor", config.DefaultKeyOffOutlineColor))

        self.typ          = keysection.get("Ktype","ONOFF")
        rt                = keysection.get("Krunthen","")
        self.Krunthen     = isysetup.ISYsetup.ProgramDict[rt] if rt <> "" else None
        self.sceneproxy   = keysection.get("sceneproxy","")
        # dummy values


        # map the key to a scene or device - prefer to map to a scene so check that first
        # Obj is the representation of the ISY Object itself, addr is the address of the ISY device/scene
        if keyname in isysetup.ISYsetup.SceneDict:
            self.addr = isysetup.ISYsetup.SceneDict[keyname].addr
            self.Obj = isysetup.ISYsetup.SceneDict[keyname]
            debugprint(config.dbgscreenbuild, "Scene ", keyname, " using ", self.Obj.name, "/", self.Obj.addr)
        elif keyname in isysetup.ISYsetup.NodeDict:
            self.addr = isysetup.ISYsetup.NodeDict[keyname].addr
            self.Obj = isysetup.ISYsetup.NodeDict[keyname]
        else:
            self.addr = ""
            self.Obj = None

        if self.typ in ("ONOFF"):
            if self.addr == "":
                print "Unbound on/off key: ", self.label
                config.ErrorItems.append("Key binding: " + self.label)
        elif self.typ in ("ONBLINKRUNTHEN"):
            self.State = False
            if self.Krunthen == None:
                print "Unbound program key: ", self.label
                config.ErrorItems.append("Prog binding: " + self.label)
        else:
            print "Unknown key type: ", self.label
            config.ErrorItems.append("Bad keytype: " + self.label)

        if isinstance(self.Obj, isysetup.SceneItem) and self.sceneproxy <> "":
            # if key is for scene and explicit proxy, push down the explicit over the default
            debugprint(config.dbgscreenbuild, "Proxying key ", self.name, " with ", self.sceneproxy)
            self.Obj.proxy = self.sceneproxy

        debugprint(config.dbgscreenbuild,repr(self))
        
        
        
    def __repr__(self):
        return "KeyDesc:"+self.name+"|ST:"+str(self.State)+"|Clr:"+str(self.backcolor)+"|OnC:"+str(self.charcoloron)+"|OffC:"\
        +str(self.charcoloroff)+"\n\r        |Lab:"+str(self.label)+"|Typ:"+self.typ+"|Adr:"+self.addr+"|Px:"+str(self.sceneproxy)+\
        "\n\r        |Ctr:"+str(self.Center)+"|Sz:"+str(self.Size)
    
