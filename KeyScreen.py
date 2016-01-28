import PyISY
import ISYSetup
import DisplayScreen
import webcolors
import config
from config import debugprint, WAITNORMALBUTTON, WAITTIMEOUT, WAITCONTROLBUTTON, WAITRANDOMTOUCH, WAITISYCHANGE, WAITEXTRACONTROLBUTTON, WAITGOHOME
import functools
from configobj import Section
wc = webcolors.name_to_rgb
import Screen

class KeyDesc:
    # Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU 
    
    def __init__(self, keysection, keyname):
        debugprint(config.dbgscreenbuild, "             New Key Desc ", keyname)
        
        self.name = keyname
        self.backcolor    = keysection.get("Kcolor",config.Kcolor)
        self.charcoloron  = keysection.get("KOnColor",config.KOnColor)
        self.charcoloroff = keysection.get("KOffColor",config.KOffColor)
        l                 = keysection.get("label",keyname)
        self.label        = l if not isinstance(l, basestring) else [l]
        self.typ          = keysection.get("Ktype",config.Ktype)
        rt=keysection.get("Krunthen","")
        self.Krunthen     = ISYSetup.ISYsetup.ProgramDict[rt] if rt<>"" else None
        self.sceneproxy   = keysection.get("sceneproxy","")
        # dummy values
        self.State        = False
        self.Center       = (0,0)
        self.Size         = (10,10)

        if self.typ == "ONBLINKRUNTHEN" and self.Krunthen <> None:
            print self.name, " bound to run then of program ", self.Krunthen.name
        
        # map the key to a scene or device - prefer to map to a scene so check that first
        # Obj is the representation of the ISY Object itself, addr is the address of the ISY device/scene
        if keyname in ISYSetup.ISYsetup.SceneDict:
            self.addr = ISYSetup.ISYsetup.SceneDict[keyname].addr
            self.Obj = ISYSetup.ISYsetup.SceneDict[keyname]
        elif keyname in ISYSetup.ISYsetup.NodeDict:
            self.addr = ISYSetup.ISYsetup.NodeDict[keyname].addr
            self.Obj = ISYSetup.ISYsetup.NodeDict[keyname]
        else:
            self.addr = ""
            self.Obj = None
            print "Key not Node or Scene: ", keyname, " in Screen Creation"                        

        if isinstance(self.Obj,ISYSetup.SceneItem):
            # if key is for scene and explicit proxy, push down the explicit over the default
            if self.sceneproxy <> "":
                self.Obj.proxy = self.sceneproxy

        debugprint(config.dbgscreenbuild,repr(self))
        
        
        
    def __repr__(self):
        return "KeyDesc:"+self.name+"|ST:"+str(self.State)+"|Clr:"+str(self.backcolor)+"|OnC:"+str(self.charcoloron)+"|OffC:"\
        +str(self.charcoloroff)+"\n\r        |Lab:"+str(self.label)+"|Typ:"+self.typ+"|Adr:"+self.addr+"|Px:"+str(self.sceneproxy)+\
        "\n\r        |Ctr:"+str(self.Center)+"|Sz:"+str(self.Size)
    



class KeyScreenDesc(Screen.ScreenDesc):
    # Describes a Key Screen: name, background, dimtimeout, keys(dict:keyname->ord),keysbyord(array of keynames),
    
    
    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New KeyScreenDesc ",screenname)
        Screen.ScreenDesc.__init__(self, screensection, screenname)
        self.keys = {}
        self.keysbyord = []
        self.buttonsperrow = -1
        self.buttonspercol = -1
        self.subscriptionlist = {}
        
        for keyname in screensection:
            if isinstance(screensection[keyname], Section):
                NewKey = KeyDesc(screensection[keyname],keyname)
                self.keys[keyname] = NewKey
                self.keysbyord.append(keyname)
                self.NumKeys = self.NumKeys + 1                


    def __repr__(self):
        return Screen.ScreenDesc.__repr__(self)+"\r\n     KeyScreenDesc:"+":<"+str(self.keysbyord)+">"


    def HandleScreen(self,newscr=True):
        
        def BlinkKey(screen,lab,back,center,size,finalstate,cycle):
            #thistime = finalstate if cycle % 2 <> 0 else not finalstate
            DisplayScreen.draw_button(screen,lab,back,finalstate if cycle % 2 <> 0 else not finalstate,center,size)

        NumKeys = self.NumKeys
        isDim = False
        
        if newscr:
            # key screen change actually occurred
            config.screen.screen.fill(wc(self.backcolor))
            self.subscriptionlist = {}
            debugprint(config.dbgMain, "Switching to screen: ", self.name)
            for j in range(NumKeys):
                K = self.keys[self.keysbyord[j]]
                if K.addr <> "":   # Key is bound to some actual device/scene
                    if isinstance(K.Obj, ISYSetup.SceneItem):
                        # if its a scene then need to get the real time status of the proxy device via rest call which returns xml
                        state = ISYSetup.get_real_time_status(K.Obj.proxy)
                        debugprint(config.dbgMain, "Status from proxy: ",K.name, K.Obj.proxy, state)
                        subscribeas = K.Obj.proxy
                    else:
                        state = ISYSetup.get_real_time_status(K.Obj.addr)
                        debugprint(config.dbgMain, "Status from node: ", K.name, state)
                        subscribeas = K.addr
            
                    K.State = not (state == 0)  # K is off (false) only if state is 0
                    self.subscriptionlist[subscribeas] = K
                DisplayScreen.draw_button(config.screen,K.label,K.backcolor,K.State,K.Center,K.Size)
        
            DisplayScreen.draw_cmd_buttons(config.screen,self)

            debugprint(config.dbgMain, "Active Subscription List will be:")
            addressestoscanfor = []
            for i in self.subscriptionlist:
                debugprint(config.dbgMain, "  Subscribe: ",i,self.subscriptionlist[i].name," : ",self.subscriptionlist[i].addr)   
                addressestoscanfor.append(i)
            config.toDaemon.put(addressestoscanfor)
        
        
        blinkproc = None
        blinktime = 0
        blinks = 0
        resetH = True
        
        while 1:
            choice = config.screen.NewWaitPress(self, config.DimTO, callbackint=blinktime,callbackproc=blinkproc,callbackcount=blinks,resetHome=resetH)
            resetH = False
            blinkproc = None
            blinktime = 0
            blinks = 0
            if not DisplayScreen.dim_change(choice):
                if choice[0] == WAITNORMALBUTTON:
                    resetH = True
                    # handle various keytype cases
                    K = self.keys[self.keysbyord[choice[1]]]
                    if K.typ == "ONOFF":
                        K.State = not K.State
                        if K.addr <> "":
                            if K.State:
                                config.ConnISY.myisy.nodes[K.addr].on()
                            else:
                                config.ConnISY.myisy.nodes[K.addr].off()
                        else:
                            #print "no on/off addr"
                            pass
                        DisplayScreen.draw_button(config.screen,K.label,K.backcolor,K.State,K.Center,K.Size)
                    elif K.typ == "ONBLINKRUNTHEN":
                        K.Krunthen.runThen()
                        blinkproc = functools.partial(BlinkKey,config.screen,K.label,K.backcolor,K.Center,K.Size,False)
                        blinktime = .5
                        blinks = 7
                        DisplayScreen.draw_button(config.screen,K.label,K.backcolor,True,K.Center,K.Size)
                        # leave K.State as is - key will return to off at end
                    elif K.typ == "ONOFFRUN":
                        pass
                elif choice[0] == WAITCONTROLBUTTON:
                    resetH = True
                    return choice[1]
                elif choice[0] == WAITRANDOMTOUCH:
                    resetH = True
                    pass
                elif choice[0] == WAITGOHOME:
                    return config.HomeScreen
                    
                elif choice[0] == WAITISYCHANGE:
                    K = self.keys[self.subscriptionlist[choice[1][0]].name]
                    ActState = int(choice[1][1]) <> 0

                    if ActState <> K.State:
                        K.State =  ActState
                        DisplayScreen.draw_button(config.screen,K.label,K.backcolor,K.State,K.Center,K.Size)
            else:
                if not config.isDim:
                    resetH = True


