import functools

import webcolors
from configobj import Section
import config
import isy
import screen
import keydesc
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITISYCHANGE, WAITEXIT

wc = webcolors.name_to_rgb


def ButLayout(butcount):
    """

    :param butcount:
    :rtype: tuple
    """
    if butcount == 0:
        return 1, 1
    if 0 < butcount < 5:
        return 1, butcount
    elif 4 < butcount < 9:
        return 2, 4
    elif 8 < butcount < 13:
        return 3, 4
    elif 12 < butcount < 17:
        return 4, 4
    elif 16 < butcount < 21:
        return 4, 5
    else:
        return -1, -1


def ButSize(bpr, bpc):
    return (
        (config.screenwidth - 2*config.horizborder)/bpr,
        (config.screenheight - config.topborder - config.botborder)/bpc)


class KeyScreenDesc(screen.ScreenDesc):
    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New KeyScreenDesc ", screenname)
        screen.ScreenDesc.__init__(self, screensection, screenname, ())  # no extra cmd keys
        self.buttonsperrow = -1
        self.buttonspercol = -1
        self.subscriptionlist = {}

        # Build the Key objects
        for keyname in screensection:
            if isinstance(screensection[keyname], Section):
                NewKey = keydesc.KeyDesc(screensection[keyname], keyname)
                self.keysbyord.append(NewKey)

        # Compute the positions and sizes for the Keys and store in the Key objects
        bpr, bpc = ButLayout(len(self.keysbyord))
        self.buttonsperrow = bpr
        self.buttonspercol = bpc
        buttonsize = ButSize(bpr, bpc)
        hpos = []
        vpos = []
        for i in range(bpr):
            hpos.append(config.horizborder + (.5 + i)*buttonsize[0])
        for i in range(bpc):
            vpos.append(config.topborder + (.5 + i)*buttonsize[1])

        for i in range(len(self.keysbyord)):
            K = self.keysbyord[i]
            K.Center = (hpos[i%bpr], vpos[i//bpr])
            K.Size = buttonsize

    def __repr__(self):
        return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.keysbyord) + ">"

    def HandleScreen(self, newscr=True):

        def BlinkKey(scr, key, cycle):
            # thistime = finalstate if cycle % 2 <> 0 else not finalstate
            key.State = not key.State
            config.DS.draw_button(scr, key)

        if newscr:
            # key screen change actually occurred
            config.screen.fill(wc(self.BackgroundColor))
            self.subscriptionlist = {}
            debugprint(config.dbgMain, "Switching to screen: ", self.name)
            for K in self.keysbyord:
                if K.MonitorObj is not None:
                    # skip program buttons
                    self.subscriptionlist[K.MonitorObj.address] = K
            states = isy.get_real_time_status(self.subscriptionlist.keys())
            for K in self.keysbyord:
                if K.MonitorObj is not None:
                    K.State = not (states[K.MonitorObj.address] == 0)  # K is off (false) only if state is 0
                config.DS.draw_button(config.screen, K)

            config.DS.draw_cmd_buttons(config.screen, self)

            debugprint(config.dbgMain, "Active Subscription List will be:")
            addressestoscanfor = ["Status"]
            for i in self.subscriptionlist:
                debugprint(config.dbgMain, "  Subscribe: ", i, self.subscriptionlist[i].name, " : ",
                           self.subscriptionlist[i].RealObj.name, ' via ', self.subscriptionlist[i].MonitorObj.name)
                addressestoscanfor.append(i)
            config.toDaemon.put(addressestoscanfor)
        else:
            debugprint(config.dbgMain, "Skipping screen recreation: ", self.name)

        blinkproc = None
        blinktime = 0
        blinks = 0

        while 1:
            choice = config.DS.NewWaitPress(self, callbackint=blinktime, callbackproc=blinkproc, callbackcount=blinks)
            blinkproc = None
            blinktime = 0
            blinks = 0
            if (choice[0] == WAITNORMALBUTTON) or (choice[0] == WAITNORMALBUTTONFAST):
                # handle various keytype cases
                K = self.keysbyord[choice[1]]
                if K.type == "ONOFF":
                    K.State = not K.State
                    if K.RealObj is not None:
                        K.RealObj.SendCommand(K.State, choice[0] <> WAITNORMALBUTTON)
                        # config.Logs.Log("Sent command to " + K.RealObj.name)
                    else:
                        config.Logs.Log("Screen: " + self.name + " press unbound key: " + K.name)
                    config.DS.draw_button(config.screen, K)
                elif K.type == "ONBLINKRUNTHEN":
                    # force double tap for programs for safety - too easy to accidentally single tap with touchscreen
                    if choice[0] == WAITNORMALBUTTONFAST:
                        K.Krunthen.runThen()
                        blinkproc = functools.partial(BlinkKey, config.screen, K)
                        blinktime = .5
                        blinks = 8  # even number leaves final state of key same as initial state
                        config.DS.draw_button(config.screen, K)
                        # leave K.State as is - key will return to off at end
                elif K.type == "ONOFFRUN":
                    pass
            elif choice[0] == WAITEXIT:
                return choice[1]
            elif choice[0] == WAITISYCHANGE:
                K = self.subscriptionlist[choice[1][0]]
                ActState = int(choice[1][1]) <> 0

                if ActState <> K.State:
                    K.State = ActState
                    config.DS.draw_button(config.screen, K)


config.screentypes["Keypad"] = KeyScreenDesc
