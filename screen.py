import config
import toucharea


def FlatenScreenLabel(label):
    scrlabel = ""
    for s in label:
        scrlabel = scrlabel + " " + s
    return scrlabel


class ScreenDesc:
    def SetExtraCmdTitles(self, titles):
        for i in range(len(titles)):
            self.ExtraCmdKeys[i].label = titles[i]

    def __init__(self, screensection, screenname, ExtraCmdButs):
        self.name = screenname
        l = screensection.get("label", screenname)
        self.label = l if not isinstance(l, basestring) else [l]
        self.backcolor = screensection.get("Bcolor", config.DefaultBkgndColor)

        self.dimtimeout = config.DimTO
        self.NextScreen = None  # for navigation buttons
        self.PrevScreen = None

        self.keysbyord = []

        CmdKeyColor = screensection.get("CmdKeyCol", config.CmdKeyCol)
        CmdCharColor = screensection.get("CmdCharCol", config.CmdCharCol)

        cbutwidth = (config.screenwidth - 2*config.horizborder)/(2 + len(ExtraCmdButs))
        cvertcenter = config.screenheight - config.botborder/2
        cbutheight = config.botborder - config.cmdvertspace*2

        self.PrevScreenKey = toucharea.ManualKeyDesc('**prev**', '**prev**',
                                                     (config.horizborder + .5*cbutwidth, cvertcenter),
                                                     (cbutwidth, cbutheight),
                                                     CmdKeyColor, CmdCharColor, CmdCharColor)
        self.NextScreenKey = toucharea.ManualKeyDesc('**next**', '**next**',
                                                     (config.horizborder + (1 + len(ExtraCmdButs) + .5)*cbutwidth,
                                                      cvertcenter), (cbutwidth, cbutheight),
                                                     CmdKeyColor, CmdCharColor, CmdCharColor)

        self.ExtraCmdKeys = []
        for i in range(len(ExtraCmdButs)):
            hcenter = config.horizborder + (i + 1.5)*cbutwidth
            self.ExtraCmdKeys.append(toucharea.ManualKeyDesc(ExtraCmdButs[i], ExtraCmdButs[i],
                                                             (hcenter, cvertcenter), (cbutwidth, cbutheight),
                                                             CmdKeyColor, CmdCharColor, CmdCharColor))

    def FinishScreen(self):
        self.PrevScreenKey.label = self.PrevScreen.label
        self.NextScreenKey.label = self.NextScreen.label

    def __repr__(self):
        return "ScreenDesc:" + self.name + ":" + self.backcolor + ":" + str(self.dimtimeout) + ":"
