import config

class ScreenDesc:
    
    def __init__(self, screensection, screenname):  
        self.name = screenname
        l = screensection.get("label",screenname)
        self.label = l if not isinstance(l, basestring) else [l]
        self.backcolor = screensection.get("Bcolor",config.BColor)
        
        self.dimtimeout       = config.DimTO
        self.NumKeys          = 0 # this makes wait key press ok no matter the type of screen
        self.NextScreen       = None # for navigation buttons
        self.NextScreenButCtr = (0,0)
        self.PrevScreen       = None
        self.PrevScreenButCtr = (0,0)
        self.CmdButSize       = (0,0)
        self.CmdKeyColor      = screensection.get("CmdKeyCol",config.CmdKeyCol)
        self.CmdCharColor     = screensection.get("CmdCharCol",config.CmdCharCol)
        self.ExtraCmdKeys     = 0     # allows for no extra keys
        self.ExtraCmdKeysCtr  = []    # elements are (x,y) tuples with centers of keys, size is same CmdButSize (all same)
        
                    
        
        
    def __repr__(self):
        return "ScreenDesc:"+self.name+":"+self.backcolor+":"+str(self.dimtimeout)+":"+str(self.NumKeys)
        

