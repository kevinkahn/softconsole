import os
import config
import pygame
import webcolors
import ButLayout
import time
from config import debugprint, WAITNORMALBUTTON, WAITTIMEOUT, WAITCONTROLBUTTON, WAITRANDOMTOUCH, WAITISYCHANGE, WAITEXTRACONTROLBUTTON, WAITGOHOME


wc = webcolors.name_to_rgb



def dim_change(c):
    if config.isDim and ((c[0] == WAITNORMALBUTTON) or (c[0] == WAITRANDOMTOUCH) or(c[0] == WAITCONTROLBUTTON)):
        config.backlight.ChangeDutyCycle(config.BrightLevel)
        config.isDim = False
        return True
    elif c[0] == WAITTIMEOUT:
        # Time out - dim
        config.isDim = True
        config.backlight.ChangeDutyCycle(config.DimLevel)
        return True
    else:
        return False

def draw_cmd_buttons(scr,AS):
    draw_button(scr,AS.PrevScreen.label,AS.CmdKeyColor,True,AS.PrevScreenButCtr,AS.CmdButSize)
    draw_button(scr,AS.NextScreen.label,AS.CmdKeyColor,True,AS.NextScreenButCtr,AS.CmdButSize)
    for i in range(AS.ExtraCmdKeys):
        draw_button(scr,AS.ExtraCmdTitles[i],AS.CmdKeyColor,True,AS.ExtraCmdKeysCtr[i],AS.CmdButSize)

def draw_button(dispscreen, txt, color, on, Center, size, shrink=True, firstfont=0):

    screen = dispscreen.screen
    lines = len(txt)
    buttonsmaller = (size[0] - 6, size[1] - 6)
    x = Center[0] - size[0]/2
    y = Center[1] - size[1]/2
    if on :
        HiColor = wc("white")
    else :
        HiColor = wc("black")
    pygame.draw.rect(screen, wc(color), ((x,y), size), 0)
    pygame.draw.rect(screen, HiColor, ((x+3,y+3), buttonsmaller), 3)
    s = pygame.Surface(size)
    s.set_alpha(150)
    s.fill(wc("white"))
    
    if on == False :
        screen.blit(s, (x,y))
    # compute writeable area for text
    textarea = (buttonsmaller[0]-6,buttonsmaller[1]-1)
    fontchoice = firstfont
    if shrink:
        for l in range(lines):
            for i in range(fontchoice,len(ButLayout.ButtonFonts)):
                txtsize = ButLayout.ButtonFonts[fontchoice].size(txt[l])
                if lines*txtsize[1] >= textarea[1] or txtsize[0] >= textarea[0]:
                    fontchoice = i
                    
    for i in range(lines) :
        #ren = pygame.transform.rotate(dispscreen.MyFont.render(txt[i], 0, HiColor), 0)
        ren = ButLayout.ButtonFonts[fontchoice].render(txt[i], 0, HiColor)
        vert_off = ((i+1)*size[1]/(1+lines)) - ren.get_height()/2
        horiz_off = (size[0] - ren.get_width())/2
        screen.blit(ren,(x+horiz_off, y+vert_off))
        
    pygame.display.update()
    

class DisplayScreen:
    screen = None

    
    def __init__(self):
        "Ininitializes a new pygame screen using the framebuffer"
        os.environ['SDL_FBDEV'] = '/dev/fb1'
        os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
        os.environ['SDL_MOUSEDRV'] = 'TSLIB'
        os.environ['SDL_VIDEODRIVER'] = 'fbcon'

        pygame.display.init()
        config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.screen = pygame.display.set_mode((config.screenwidth,config.screenheight), pygame.FULLSCREEN)
        # Clear the screen to start
        self.screen.fill((0, 0, 0))  

        # Initialise font support
        pygame.font.init()
        # Render the screen
        pygame.display.update()
        pygame.mouse.set_visible(False)
        pygame.font.init()
        
        # define user events
        self.MAXTIMEHIT = pygame.event.Event(pygame.USEREVENT)
        self.INTERVALHIT = pygame.event.Event(pygame.USEREVENT+1)
        self.GOHOMEHIT = pygame.event.Event(pygame.USEREVENT+2)
  
   

    def NewWaitPress(self,ActiveScreen,maxwait=0,callbackint=0,callbackproc=None,callbackcount=0):
        """
        wait for a mouse click a maximum of maxwait seconds
        if callbackint <> 0 call the callbackproc every callbackint time
        return tuple (reason, keynum) with (0, keynum) reg press, (1,0) timeout, (2,keynum) ctl press (3,0) random press
        (4,keyname) ISY event on device associated with keyname  
        (5,keyname) blink need on device associated with keyname???
        """

        if callbackint <> 0:
            pygame.time.set_timer(self.INTERVALHIT.type, int(callbackint*1000))
        cycle = callbackcount if callbackcount <> 0 else 100000000  # essentially infinite
        if maxwait <> 0:
            pygame.time.set_timer(self.MAXTIMEHIT.type, maxwait*1000)
        
        while True:
            if not config.fromDaemon.empty():
                alert = config.fromDaemon.get()
                debugprint(config.dbgMain, time.time(),"ISY reports change: ","Key: ", alert)
                rtn = (WAITISYCHANGE,alert)
                break
            event = pygame.fastevent.poll()
            
            if event.type == pygame.NOEVENT:
                time.sleep(.2)

            #print "Waitloop: ",time.time()
            #print "Event",event
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # on any touch reset return to home screen
                pygame.time.set_timer(self.GOHOMEHIT.type, int(config.HomeScreenTO)*1000)
                found = False
                pos = (pygame.mouse.get_pos()[0],pygame.mouse.get_pos()[1])
                
                for i in range(ActiveScreen.NumKeys):
                    K = ActiveScreen.keys[ActiveScreen.keysbyord[i]]
                    if ButLayout.InBut(pos, K.Center, K.Size):
                        rtn = (WAITNORMALBUTTON, i)
                        found = True
           
                if ButLayout.InBut(pos,ActiveScreen.PrevScreenButCtr,ActiveScreen.CmdButSize):
                    rtn = (WAITCONTROLBUTTON, ActiveScreen.PrevScreen)
                    found = True
                elif ButLayout.InBut(pos,ActiveScreen.NextScreenButCtr,ActiveScreen.CmdButSize):
                    rtn = (WAITCONTROLBUTTON, ActiveScreen.NextScreen)
                    found = True
                else:
                    for i in range(ActiveScreen.ExtraCmdKeys):
                        if ButLayout.InBut(pos, ActiveScreen.ExtraCmdKeysCtr[i], ActiveScreen.CmdButSize):
                            rtn = (WAITEXTRACONTROLBUTTON, i)
                            found = True
                if not found:
                    rtn = (WAITRANDOMTOUCH, 0)
                break
            
            elif event.type == self.MAXTIMEHIT.type:
                rtn = (WAITTIMEOUT,0)
                break
            elif event.type == self.INTERVALHIT.type:
                if (callbackproc <> None) and (cycle > 0):
                    callbackproc(cycle)
                    cycle -= 1
            elif event.type == self.GOHOMEHIT.type:
                rtn = (WAITGOHOME,0)
                break
            else:
                pass # ignore and flush other events
            
        pygame.time.set_timer(self.INTERVALHIT.type, 0)
        pygame.time.set_timer(self.MAXTIMEHIT.type, 0)
        
        return rtn
    
