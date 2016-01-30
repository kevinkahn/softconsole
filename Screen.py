import config

class ScreenDesc:
    
    def SetExtraCmdTitles(self, titles):
        self.ExtraCmdTitles   = titles
        # Titles are a list of tuples, one list item per button with tuple as the text string(s)
        
    
    def __init__(self, screensection, screenname, ExtraCmdButs):  
        self.name = screenname
        l = screensection.get("label",screenname)
        self.label = l if not isinstance(l, basestring) else [l]
        self.backcolor = screensection.get("Bcolor",config.BColor)
        
        self.dimtimeout       = config.DimTO
        self.NumKeys          = 0 # this makes wait key press ok no matter the type of screen
        self.NextScreen       = None # for navigation buttons
        self.PrevScreen       = None
        
        self.CmdKeyColor      = screensection.get("CmdKeyCol",config.CmdKeyCol)
        self.CmdCharColor     = screensection.get("CmdCharCol",config.CmdCharCol)
        self.ExtraCmdKeys     = ExtraCmdButs     # allows for no extra keys
        
        numcmdbuts = 2 + ExtraCmdButs
        cbutwidth = (config.screenwidth-2*config.horizborder)/numcmdbuts
        cvertcenter = config.screenheight - config.botborder/2 
        cbutheight = config.botborder - config.cmdvertspace*2
        
        self.CmdButSize       = (cbutwidth, cbutheight)
        self.PrevScreenButCtr = (config.horizborder + .5*cbutwidth, cvertcenter)
        self.NextScreenButCtr = (config.horizborder + ((numcmdbuts-1)+.5)*cbutwidth, cvertcenter)
    
        self.ExtraCmdKeysCtr  = []    # elements are (x,y) tuples with centers of keys, size is same CmdButSize (all same)
        self.ExtraCmdTitles   = []
        for i in range(ExtraCmdButs):
            hcenter = config.horizborder + (i+1.5)*cbutwidth
            self.ExtraCmdKeysCtr.append((hcenter, cvertcenter))
            self.ExtraCmdTitles.append(('**missing**',))

    def __repr__(self):
        return "ScreenDesc:"+self.name+":"+self.backcolor+":"+str(self.dimtimeout)+":"+str(self.NumKeys)
        

