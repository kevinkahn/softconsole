from configobj import Section

import config
from config import debugprint
from logsupport import Warning


class MyScreens:
    def __init__(self):

        Logs = config.Logs
        thisconfig = config.ParsedConfigFile

        debugprint(config.dbgscreenbuild, "Process Configuration File")

        mainlist = {}
        secondlist = {}
        extralist = {}

        for screenitem in thisconfig:
            NewScreen = None
            if isinstance(thisconfig[screenitem], Section):
                thisScreen = thisconfig[screenitem]
                # its a screen
                tempscreentype = thisScreen.get("typ", "unspec")
                debugprint(config.dbgscreenbuild, "Screen of type ", tempscreentype)

                if tempscreentype in config.screentypes:
                    NewScreen = config.screentypes[tempscreentype](thisScreen, screenitem)
                    Logs.Log(tempscreentype + " screen " + screenitem)
                else:
                    Logs.Log("Screentype error" + screenitem + " type " + tempscreentype, Warning)
                    pass
            if NewScreen <> None:
                # set the standard navigation keys and navigation linkages
                if NewScreen.name in config.MainChain:
                    mainlist[NewScreen.name] = NewScreen
                elif NewScreen.name in config.SecondaryChain:
                    secondlist[NewScreen.name] = NewScreen
                else:
                    extralist[NewScreen.name] = NewScreen
                    config.ExtraChain.append(NewScreen.name)

        if len(secondlist) == 0:
            secondlist = extralist
            config.SecondaryChain = config.ExtraChain
            config.ExtraChain = []
        Logs.Log("Main Screen List:")
        for scr in config.MainChain:
            S = mainlist[scr]
            S.PrevScreen = mainlist[config.MainChain[config.MainChain.index(scr) - 1]]
            S.NextScreen = mainlist[config.MainChain[(config.MainChain.index(scr) + 1)%len(config.MainChain)]]
            Logs.Log("   " + scr)

        Logs.Log("Secondary Screen List:")
        for scr in config.SecondaryChain:
            S = secondlist[scr]
            S.PrevScreen = secondlist[config.SecondaryChain[config.SecondaryChain.index(scr) - 1]]
            S.NextScreen = secondlist[
                config.SecondaryChain[(config.SecondaryChain.index(scr) + 1)%len(config.SecondaryChain)]]
            Logs.Log("   " + scr)

        Logs.Log("Not on a screen list (unavailable)", Warning)
        for scr in config.ExtraChain:
            Logs.Log("   " + scr, Warning)

        for S in mainlist.itervalues():
            S.FinishScreen()
        for S in secondlist.itervalues():
            S.FinishScreen()

        if config.HomeScreenName in config.MainChain:
            config.HomeScreen = mainlist[config.HomeScreenName]
        else:
            config.HomeScreen = mainlist[0]

        config.HomeScreen2 = secondlist[config.SecondaryChain[0]]

        Logs.Log("Home Screen: " + config.HomeScreen.name)
        if config.DimHomeScreenCoverName in config.MainChain:
            config.DimHomeScreenCover = mainlist[config.DimHomeScreenCoverName]
            Logs.Log("Dim Home Screen: " + config.DimHomeScreenCover.name)
        else:
            config.DimHomeScreenCover = config.HomeScreen
            Logs.Log("No Dim Home Screen Cover Set")
        Logs.Log("First Secondary Screen: " + config.HomeScreen2.name)
