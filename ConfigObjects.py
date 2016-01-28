from configobj import Section
import ISYSetup
import DisplayScreen
import ButLayout
import config
from config import *
from config import debugprint, dbgscreenbuild
import Screen, ClockScreen, KeyScreen




class MyScreens:
    
    #screentype = dict()   # dict keyed by name of screen; entries are screentype, dict(keyname,keynumber),list keynames indexed by keynum 
    """
    screenlist: dict (screenname -> (screentype,screenordinal,appropriate xxxScreenDesc)
    """
    screenlist = {}


    def __init__(self):
        thisconfig = config.ParsedConfigFile   
        
        debugprint(dbgscreenbuild, "Process Configuration File")
        
        config.DimLevel    = int(thisconfig.get("DimLevel",config.DimLevel))
        config.BrightLevel = int(thisconfig.get("BrightLevel",config.BrightLevel))
        config.DimTO       = int(thisconfig.get("DimTO",config.DimTO))
        config.CmdKeyCol   = str(thisconfig.get("CmKeyColor",config.CmdKeyCol))
        config.CmdCharCol  = str(thisconfig.get("CmdCharCol",config.CmdCharCol))
        prevscreen = None
        firstscreen = None
        
        for screenitem in thisconfig:
            NewScreen = None
            if isinstance(thisconfig[screenitem], Section):
                thisScreen = thisconfig[screenitem]
                #its a screen
                tempscreentype = thisScreen.get("typ","unspec")
                bkgcolor = thisScreen.get("Bcolor",config.BColor)
                lab = thisScreen.get("label",screenitem)
                debugprint(dbgscreenbuild, "Screen of type ", tempscreentype)
                
                if tempscreentype == "Keys":
                    # Key Screen
                    NewScreen = KeyScreen.KeyScreenDesc(screenitem,bkgcolor,lab)
                    # NewScreen = KeyScreen.KeyScreenDesc(thisscreen) pass in the config "section" and let the init do the parsing
                    # then need to decide who parses the key info - the screen init or here? doing it here sort of violates obj structure
                    # in that this proc then knows about innerds of keyscreen having keys - is that bad?
                    
                    # now parse the keys
                    
                    for tmpkey in thisScreen:
                        keyparams = thisScreen[tmpkey]
                        debugprint(dbgscreenbuild, "  Item: ",tmpkey, " is ", keyparams)
                        if isinstance(keyparams, Section):
                            
                            # key description
                            
                            if tmpkey in ISYSetup.ISYsetup.SceneDict:
                                # prefer to map the key to a Scene (in case it is also the name of a Node)
                                Taddr = ISYSetup.ISYsetup.SceneDict[tmpkey].addr
                                TObj = ISYSetup.ISYsetup.SceneDict[tmpkey]
                            elif tmpkey in ISYSetup.ISYsetup.NodeDict:
                                Taddr = ISYSetup.ISYsetup.NodeDict[tmpkey].addr
                                TObj = ISYSetup.ISYsetup.NodeDict[tmpkey]
                            else:
                                Taddr = ""
                                TObj = None
                                print "Key not Node or Scene: ", tmpkey, " in Screen ", screenitem                            
                            
                            NewKey = KeyScreen.KeyDesc(tmpkey,                             adr = Taddr\
                            , O = TObj,                                          bkg=keyparams.get("Kcolor",config.Kcolor)\
                            , keyon=keyparams.get("KOnColor",config.KOnColor),   keyoff=keyparams.get("KOffColor",config.KOffColor)\
                            , klab=keyparams.get("label",tmpkey),                ktyp=keyparams.get("Ktype",config.Ktype)\
                            , sprox=keyparams.get("sceneproxy",""),              rt=keyparams.get("Krunthen","")\
                            , OffU="")
                            NewScreen.AddKey(tmpkey, NewKey)

                            debugprint(dbgscreenbuild,repr(NewKey))
                        
                    CmdCtrs, NewScreen.CmdButSize = ButLayout.LayoutScreen(NewScreen.NumKeys, NewScreen,0) # no extra command buttons
                    
                elif tempscreentype == "Clock":
                    debugprint(dbgscreenbuild, "Build Clock Screen")
                    clkparam = thisconfig[screenitem]
                    cmdclr = clkparam.get("CmdKeyCol",config.CmdKeyCol)
                    cmdchar = clkparam.get("CmdCharCol",config.CmdCharCol)
                    NewScreen = ClockScreen.ClockScreenDesc(screenitem, bkgcolor, lab\
                    , clkparam.get("CharCol",config.CharCol), clkparam.get("OutFormat",""), clkparam.get("CharSize",config.CharSize))
                    NewScreen.CmdKeyColor = cmdclr
                    NewScreen.CmdCharColor = cmdchar
                    CmdCtrs, NewScreen.CmdButSize = ButLayout.LayoutScreen(0, None,0)
                    
                elif tempscreentype == "deviceall":
                    debugprint(dbgscreenbuild, "Build Deviceall Screen")
                    # all devices screen(s)
                    pass
                    
                else:
                    debugprint(dbgscreenbuild, "Unknown Screen")
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

        
            
            
        
            

    