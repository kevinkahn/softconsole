import config


def InBut(pos,center,size):
    if (pos[0] > center[0] - size[0]/2) and (pos[0] < center[0] + size[0]/2) and (pos[1] > center[1] - size[1]/2) and (pos[1] < center[1] + size[1]/2):
        return True
    else:
        return False
        
def LayoutScreen(butcount,KeyScreen,ExtraCmdButs):
    
    if KeyScreen <> None:
        bpr, bpc = ButLayout(butcount)
        KeyScreen.buttonsperrow = bpr
        KeyScreen.buttonspercol = bpc
        buttonsize = ButSize(bpr,bpc)
        hpos = []
        vpos = []
        for i in range(bpr) :
            hpos.append(config.horizborder + (.5+i)*buttonsize[0])
        for i in range(bpc) :
            vpos.append(config.topborder + (.5+i)*buttonsize[1])
        
        for i in range(butcount):
            K = KeyScreen.keys[KeyScreen.keysbyord[i]]
            K.Center = (hpos[i%bpr], vpos[i//bpr])
            K.Size = buttonsize

    numcmdbuts = 2 + ExtraCmdButs
    cbutwidth = (config.screenwidth-2*config.horizborder)/numcmdbuts
    cmdvertspace = 10 # this is the space around the top/bot of button within the bot border
    cvertcenter = config.screenheight - config.botborder/2 
    cbutheight = config.botborder - cmdvertspace*2
    CmdCenters = []
    for i in range(numcmdbuts):
        hcenter = config.horizborder + (i+.5)*cbutwidth
        CmdCenters.append((hcenter, cvertcenter))   
    return (CmdCenters,(cbutwidth,cbutheight))

def ButLayout(butcount):
    if butcount == 0:
        return (1, 1)
    if butcount > 0 and butcount < 5 :
        return (1, butcount)
    elif butcount > 4 and butcount < 9 :
        return (2, 4)
    elif butcount > 8 and butcount < 13 :
        return (3, 4)
    elif butcount > 12 and butcount < 17 :
        return (4, 4)
    elif butcount > 16 and butcount < 21 :
        return (4, 5)
    else :
        return (-1, -1)

def ButSize(bpr,bpc):
    return ((config.screenwidth - 2*config.horizborder)/bpr, (config.screenheight - config.topborder - config.botborder)/bpc)

