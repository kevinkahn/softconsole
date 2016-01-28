from configobj import Section
import ISYSetup
import DisplayScreen
import ButLayout
import config
from config import debugprint
import Screen, ClockScreen, KeyScreen




class MyScreens:
    
    #screentype = dict()   # dict keyed by name of screen; entries are screentype, dict(keyname,keynumber),list keynames indexed by keynum 
    """
    screenlist: dict (screenname -> (screentype,screenordinal,appropriate xxxScreenDesc)
    """
    screenlist = {}


    def __init__(self):
        thisconfig = config.ParsedConfigFile   
        
        debugprint(config.dbgscreenbuild, "Process Configuration File")
        
        
        prevscreen = None
        firstscreen = None
        
        for screenitem in thisconfig:
            NewScreen = None
            if isinstance(thisconfig[screenitem], Section):
                thisScreen = thisconfig[screenitem]
                #its a screen
                tempscreentype = thisScreen.get("typ","unspec")
                debugprint(config.dbgscreenbuild, "Screen of type ", tempscreentype)
                
                if tempscreentype == "Keys":
                    # Key Screen
                    NewScreen = KeyScreen.KeyScreenDesc(thisScreen, screenitem)
                    CmdCtrs, NewScreen.CmdButSize = ButLayout.LayoutScreen(NewScreen.NumKeys, NewScreen,0) # no extra command buttons
                    
                elif tempscreentype == "Clock":
                    # Clock Screen
                    NewScreen = ClockScreen.ClockScreenDesc(thisScreen, screenitem)
                    CmdCtrs, NewScreen.CmdButSize = ButLayout.LayoutScreen(0, None,0)
                    
                elif tempscreentype == "deviceall":
                    debugprint(config.dbgscreenbuild, "Build Deviceall Screen")
                    # all devices screen(s)
                    pass
                    
                else:
                    debugprint(config.dbgscreenbuild, "Unknown Screen")
                    # unknown - skip
                    pass
            
            if NewScreen <> None:
                # set the standard navigation keys and navigation linkages
                NewScreen.PrevScreenButCtr = CmdCtrs[0]
                NewScreen.NextScreenButCtr = CmdCtrs[len(CmdCtrs)-1] # leftmost and rightmost buttons are prev/next
                firstscreen = NewScreen if firstscreen == None else firstscreen
                prevscreen = NewScreen if prevscreen == None else prevscreen
                self.screenlist[screenitem] = NewScreen
                prevscreen.NextScreen = NewScreen 
                NewScreen.PrevScreen = prevscreen
                NewScreen.NextScreen = firstscreen
                prevscreen = NewScreen
                firstscreen.PrevScreen = NewScreen
         
        
        config.HomeScreen = self.screenlist[config.HomeScreenName]

        
            
            
        
            

    