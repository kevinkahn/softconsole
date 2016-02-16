import config
import toucharea
import utilities


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
        self.label = utilities.normalize_label(
            screensection.get("label", screenname))  # todo remove somehow? likely same inherited pkg issue _p_
        utilities.LocalizeParams(self, screensection, 'CharColor', 'DimTO', 'BackgroundColor', 'CmdKeyCol',
                                 'CmdCharCol')

        self.keysbyord = []

        cbutwidth = (config.screenwidth - 2*config.horizborder)/(2 + len(ExtraCmdButs))
        cvertcenter = config.screenheight - config.botborder/2
        cbutheight = config.botborder - config.cmdvertspace*2
        self.PrevScreenKey = toucharea.ManualKeyDesc('**prev**', '**prev**',
                                                     (config.horizborder + .5*cbutwidth, cvertcenter),
                                                     (cbutwidth, cbutheight),
                                                     self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol)
        self.NextScreenKey = toucharea.ManualKeyDesc('**next**', '**next**',
                                                     (config.horizborder + (1 + len(ExtraCmdButs) + .5)*cbutwidth,
                                                      cvertcenter), (cbutwidth, cbutheight),
                                                     self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol)
        self.ExtraCmdKeys = []
        for i in range(len(ExtraCmdButs)):
            hcenter = config.horizborder + (i + 1.5)*cbutwidth
            self.ExtraCmdKeys.append(toucharea.ManualKeyDesc(ExtraCmdButs[i], ExtraCmdButs[i], (hcenter, cvertcenter),
                                                             (cbutwidth, cbutheight),
                                                             self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol))

    def FinishScreen(self):
        self.PrevScreenKey.label = self.PrevScreen.label
        self.NextScreenKey.label = self.NextScreen.label

    def __repr__(self):
        return "ScreenDesc:" + self.name + ":" + self.BackgroundColor + ":" + str(self.DimTO) + ":"
