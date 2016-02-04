from configobj import Section
import ISYSetup
import DisplayScreen
import ButLayout
import config
from config import debugprint
import ClockScreen, KeyScreen, WeatherScreen, ThermostatScreen
import LogSupport
from LogSupport import Info, Warning, Error



class MyScreens:
    

    """
    screenlist: dict (screenname -> (screentype,screenordinal,appropriate xxxScreenDesc)
    """
    screenlist = {}


    def __init__(self):
        
        Logs = config.Logs
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
                
                if tempscreentype in config.screentypes:
                    NewScreen = config.screentypes[tempscreentype](thisScreen, screenitem)
                    Logs.Log(tempscreentype + " screen " + screenitem)
                else:
                    Logs.Log("Screentype error" + screenitem + " type " + tempscreentype,Warning)
                    pass
            
            if NewScreen <> None:
                # set the standard navigation keys and navigation linkages
                
                firstscreen = NewScreen if firstscreen == None else firstscreen
                prevscreen = NewScreen if prevscreen == None else prevscreen
                self.screenlist[screenitem] = NewScreen
                prevscreen.NextScreen = NewScreen
                NewScreen.PrevScreen = prevscreen
                NewScreen.NextScreen = firstscreen
                prevscreen = NewScreen
                firstscreen.PrevScreen = NewScreen
         
        for S in self.screenlist.itervalues():
            S.FinishScreen()
            
        if config.HomeScreenName in self.screenlist:
            config.HomeScreen = self.screenlist[config.HomeScreenName]
        else:
            config.HomeScreen = firstscreen

        
