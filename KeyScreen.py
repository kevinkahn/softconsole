import PyISY
import ISYSetup
import DisplayScreen
import TouchArea
import webcolors
import config
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITISYCHANGE, WAITEXIT
import functools
from configobj import Section
wc = webcolors.name_to_rgb
import Screen


def ButLayout(butcount):
    if butcount == 0:
        return (1, 1)
    if butcount > 0 and butcount < 5 :
        return (1, butcount)
    elif butcount > 4 and butcount < 9 :
        return (2, 4)
    elif butcount > 8 and butcount < 13 :
        return (3, 4)
    elif butcount > 12 and butcount < 17 :
        return (4, 4)
    elif butcount > 16 and butcount < 21 :
        return (4, 5)
    else :
        return (-1, -1)

def ButSize(bpr,bpc):
    return ((config.screenwidth - 2*config.horizborder)/bpr, (config.screenheight - config.topborder - config.botborder)/bpc)




class KeyScreenDesc(Screen.ScreenDesc):

    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New KeyScreenDesc ",screenname)
        Screen.ScreenDesc.__init__(self, screensection, screenname, ()) # no extra cmd keys
        self.buttonsperrow = -1
        self.buttonspercol = -1
        self.subscriptionlist = {}
        
        # Build the Key objects
        for keyname in screensection:
            if isinstance(screensection[keyname], Section):
                NewKey = TouchArea.KeyDesc(screensection[keyname],keyname)
                self.keysbyord.append(NewKey)
                
        # Compute the positions and sizes for the Keys and store in the Key objects
        bpr, bpc = ButLayout(len(self.keysbyord))
        self.buttonsperrow = bpr
        self.buttonspercol = bpc
        buttonsize = ButSize(bpr,bpc)
        hpos = []
        vpos = []
        for i in range(bpr) :
            hpos.append(config.horizborder + (.5+i)*buttonsize[0])
        for i in range(bpc) :
            vpos.append(config.topborder + (.5+i)*buttonsize[1])
        
        for i in range(len(self.keysbyord)):
            K = self.keysbyord[i]
            K.Center = (hpos[i%bpr], vpos[i//bpr])
            K.Size = buttonsize



    def __repr__(self):
        return Screen.ScreenDesc.__repr__(self)+"\r\n     KeyScreenDesc:"+":<"+str(self.keysbyord)+">"


    def HandleScreen(self,newscr=True):
        
        def BlinkKey(screen,lab,back,center,size,finalstate,cycle):
            #thistime = finalstate if cycle % 2 <> 0 else not finalstate
            DisplayScreen.draw_button(screen,lab,back,finalstate if cycle % 2 <> 0 else not finalstate,center,size)

        NumKeys = len(self.keysbyord)

        if newscr:
            # key screen change actually occurred
            config.screen.fill(wc(self.backcolor))
            self.subscriptionlist = {}
            debugprint(config.dbgMain, "Switching to screen: ", self.name)
            for j in range(len(self.keysbyord)):
                K = self.keysbyord[j]
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
            # this loop is separate from the above one only because doing so make the screen draw look more instantaneous
            for K in self.keysbyord:
                DisplayScreen.draw_button(config.screen,K)
        
            DisplayScreen.draw_cmd_buttons(config.screen,self)

            debugprint(config.dbgMain, "Active Subscription List will be:")
            addressestoscanfor = ["Status"]
            for i in self.subscriptionlist:
                debugprint(config.dbgMain, "  Subscribe: ",i,self.subscriptionlist[i].name," : ",self.subscriptionlist[i].addr)   
                addressestoscanfor.append(i)
            config.toDaemon.put(addressestoscanfor)
        
        
        blinkproc = None
        blinktime = 0
        blinks = 0
        
        while 1:
            choice = config.DS.NewWaitPress(self, callbackint=blinktime,callbackproc=blinkproc,callbackcount=blinks)
            blinkproc = None
            blinktime = 0
            blinks = 0
            if choice[0] == WAITNORMALBUTTON:
                # handle various keytype cases
                K = self.keysbyord[choice[1]]
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
                    DisplayScreen.draw_button(config.screen,K)
                elif K.typ == "ONBLINKRUNTHEN":
                    K.Krunthen.runThen()
                    blinkproc = functools.partial(BlinkKey,config.screen,K.label,K.backcolor,K.Center,K.Size,False)
                    blinktime = .5
                    blinks = 7
                    DisplayScreen.draw_button(config.screen,K)
                    # leave K.State as is - key will return to off at end
                elif K.typ == "ONOFFRUN":
                    pass
            elif choice[0] == WAITEXIT:
                return choice[1]
            elif choice[0] == WAITISYCHANGE:
                K = self.subscriptionlist[choice[1][0]]
                ActState = int(choice[1][1]) <> 0

                if ActState <> K.State:
                    K.State =  ActState
                    DisplayScreen.draw_button(config.screen,K.label,K.backcolor,K.State,K.Center,K.Size)

config.screentypes["Keys"] = KeyScreenDesc
