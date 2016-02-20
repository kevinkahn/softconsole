import config
import toucharea
import utilities
import displayscreen
import webcolors

wc = webcolors.name_to_rgb


def FlatenScreenLabel(label):
    scrlabel = ""
    for s in label:
        scrlabel = scrlabel + " " + s
    return scrlabel


def ButLayout(butcount):
    """
    :param butcount:
    :rtype: tuple
    """
    if butcount == 0:
        return 1, 1
    if 0 < butcount < 5:
        return 1, butcount
    elif 4 < butcount < 7:
        return 2, 3
    elif 6 < butcount < 9:
        return 2, 4
    elif 8 < butcount < 13:
        return 3, 4
    elif 12 < butcount < 17:
        return 4, 4
    elif 16 < butcount < 21:
        return 4, 5
    else:
        return -1, -1


def ButSize(bpr, bpc, height):
    h = config.screenheight - config.topborder - config.botborder if height == 0 else height
    return (
        (config.screenwidth - 2*config.horizborder)/bpr, h/bpc)


class ScreenDesc:
    def SetExtraCmdTitles(self, titles):
        for i in range(len(titles)):
            self.ExtraCmdKeys[i].label = titles[i]

    def __init__(self, screensection, screenname, ExtraCmdButs=(), withnav=True):
        self.name = screenname
        self.keysbyord = []
        utilities.LocalizeParams(self, screensection, 'CharColor', 'DimTO', 'BackgroundColor', 'CmdKeyCol',
                                 'CmdCharCol', label=[screenname])
        self.WithNav = withnav
        self.PrevScreen = self.NextScreen = None
        cbutwidth = (config.screenwidth - 2*config.horizborder)/(2 + len(ExtraCmdButs))
        cvertcenter = config.screenheight - config.botborder/2
        cbutheight = config.botborder - config.cmdvertspace*2
        self.PrevScreenKey = toucharea.ManualKeyDesc('**prev**', ['**prev**'],
                                                     self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
                                                     center=(config.horizborder + .5*cbutwidth, cvertcenter),
                                                     size=(cbutwidth, cbutheight))
        self.NextScreenKey = toucharea.ManualKeyDesc('**next**', ['**next**'],
                                                     self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
                                                     center=(
                                                     config.horizborder + (1 + len(ExtraCmdButs) + .5)*cbutwidth,
                                                     cvertcenter), size=(cbutwidth, cbutheight))
        self.ExtraCmdKeys = []
        for i in range(len(ExtraCmdButs)):
            hcenter = config.horizborder + (i + 1.5)*cbutwidth
            self.ExtraCmdKeys.append(toucharea.ManualKeyDesc(ExtraCmdButs[i], ExtraCmdButs[i],
                                                             self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
                                                             center=(hcenter, cvertcenter),
                                                             size=(cbutwidth, cbutheight)))

    def FinishScreen(self):
        if self.PrevScreen is None:
            self.PrevScreenKey = None
        else:
            self.PrevScreenKey.label = self.PrevScreen.label
            self.NextScreenKey.label = self.NextScreen.label

    def PaintBase(self):
        config.screen.fill(wc(self.BackgroundColor))
        if self.WithNav:
            config.DS.draw_cmd_buttons(self)


    def __repr__(self):
        return "ScreenDesc:" + self.name + ":" + self.BackgroundColor + ":" + str(self.DimTO) + ":"


class BaseKeyScreenDesc(ScreenDesc):
    def __init__(self, screensection, screenname, ExtraCmdButs=(), withnav=True):
        ScreenDesc.__init__(self, screensection, screenname, ExtraCmdButs, withnav)
        utilities.LocalizeParams(self, None)
        self.buttonsperrow = -1
        self.buttonspercol = -1

    def LayoutKeys(self, extraOffset=0, height=0):
        # Compute the positions and sizes for the Keys and store in the Key objects
        bpr, bpc = ButLayout(len(self.keysbyord))
        self.buttonsperrow = bpr
        self.buttonspercol = bpc

        buttonsize = ButSize(bpr, bpc, height)
        hpos = []
        vpos = []
        for i in range(bpr):
            hpos.append(config.horizborder + (.5 + i)*buttonsize[0])
        for i in range(bpc):
            vpos.append(config.topborder + extraOffset + (.5 + i)*buttonsize[1])

        for i in range(len(self.keysbyord)):
            K = self.keysbyord[i]
            K.Center = (hpos[i%bpr], vpos[i//bpr])
            K.Size = buttonsize

    def PaintKeys(self):
        for key in self.keysbyord:
            config.DS.draw_button(key)
