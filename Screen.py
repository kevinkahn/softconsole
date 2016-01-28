import config

class ScreenDesc:
    def __init__(self,sname,sbkg,lab):
        self.name = sname
        self.label = lab if not isinstance(lab, basestring) else [lab]
        self.backcolor = sbkg
        self.dimtimeout = config.DimTO
        self.NumKeys = 0 # this makes wait key press ok no matter the type of screen
        self.NextScreen = None # for navigation buttons
        self.NextScreenButCtr = (0,0)
        self.PrevScreen = None
        self.PrevScreenButCtr = (0,0)
        self.CmdButSize = (0,0)
        self.CmdKeyColor = config.CmdKeyCol
        self.CmdCharColor = config.CmdCharCol
        
    def __repr__(self):
        return "ScreenDesc:"+self.name+":"+self.backcolor+":"+str(self.dimtimeout)+":"+str(self.NumKeys)
        

