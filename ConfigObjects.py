from configobj import Section
import ISYSetup
import DisplayScreen
import ButLayout
import config
from config import debugprint
import Screen, ClockScreen, KeyScreen, WeatherScreen




class MyScreens:
    

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
                    NewScreen = KeyScreen.KeyScreenDesc(thisScreen, screenitem)

                elif tempscreentype == "Clock":
                    NewScreen = ClockScreen.ClockScreenDesc(thisScreen, screenitem)
                    
                elif tempscreentype == "Weather":
                    NewScreen = WeatherScreen.WeatherScreenDesc(thisScreen, screenitem)

                elif tempscreentype == "deviceall":
                    debugprint(config.dbgscreenbuild, "Build Deviceall Screen")
                    # all devices screen(s)
                    pass
                    
                else:
                    print "Unknown screen type in config file: ",tempscreentype
                    # unknown - skip
                    pass
            
            if NewScreen <> None:
                # set the standard navigation keys and navigation linkages
                
                firstscreen = NewScreen if firstscreen == None else firstscreen
                prevscreen = NewScreen if prevscreen == None else prevscreen
                self.screenlist[screenitem] = NewScreen
                prevscreen.NextScreen = NewScreen 
                NewScreen.PrevScreen = prevscreen
                NewScreen.NextScreen = firstscreen
                #print "Linking: ", NewScreen.label, " Prev: ", NewScreen.PrevScreen.label, " Next: ", NewScreen.NextScreen.label
                prevscreen = NewScreen
                firstscreen.PrevScreen = NewScreen
         
        #print "Finished linking first screen ",firstscreen.label," Prev: ", firstscreen.PrevScreen.label
        config.HomeScreen = self.screenlist[config.HomeScreenName]

        
