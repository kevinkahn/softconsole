import os
import config
import pygame
import webcolors
import ButLayout
import time
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITCONTROLBUTTON, WAITISYCHANGE, WAITEXTRACONTROLBUTTON, WAITGOHOME, WAITMAINTTAP


wc = webcolors.name_to_rgb


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

        # define user events
        self.MAXTIMEHIT = pygame.event.Event(pygame.USEREVENT)
        self.INTERVALHIT = pygame.event.Event(pygame.USEREVENT+1)
        self.GOHOMEHIT = pygame.event.Event(pygame.USEREVENT+2)
        self.isDim = False

  
   

    def NewWaitPress(self,ActiveScreen,callbackint=0,callbackproc=None,callbackcount=0):
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
        pygame.time.set_timer(self.MAXTIMEHIT.type, config.DimTO*1000)  # make sure dim timer is running on entry no harm if already dim

        
        
        while True:
            rtn = (0, 0)
            if not config.fromDaemon.empty():
                alert = config.fromDaemon.get()
                debugprint(config.dbgMain, time.time(),"ISY reports change: ","Key: ", alert)
                rtn = (WAITISYCHANGE,alert)
                break
            event = pygame.fastevent.poll()
            
            if event.type == pygame.NOEVENT:
                time.sleep(.2)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = (pygame.mouse.get_pos()[0],pygame.mouse.get_pos()[1])
                tapcount = 1
                pygame.time.delay(config.multitaptime)
                while True:
                    eventx = pygame.fastevent.poll()
                    if eventx.type == pygame.NOEVENT:
                        break
                    elif eventx.type == pygame.MOUSEBUTTONDOWN:
                        tapcount += 1
                        pygame.time.delay(config.multitaptime)
                    else:
                        continue
                if tapcount > 3:
                    print "maint return", tapcount
                    rtn = (WAITMAINTTAP, tapcount)
                    break
                # on any touch reset return to home screen
                pygame.time.set_timer(self.GOHOMEHIT.type, int(config.HomeScreenTO)*1000)
                # on any touch restart dim timer and reset to bright if dim
                pygame.time.set_timer(self.MAXTIMEHIT.type, config.DimTO*1000)
                if self.isDim:
                    config.backlight.ChangeDutyCycle(config.BrightLevel)
                    self.isDim = False
                    continue  # touch that ends dim screen is otherwise ignored
                
                
                for i in range(ActiveScreen.NumKeys):
                    K = ActiveScreen.keys[ActiveScreen.keysbyord[i]]
                    if ButLayout.InBut(pos, K.Center, K.Size):
                        rtn = (WAITNORMALBUTTON, i)
                if ButLayout.InBut(pos,ActiveScreen.PrevScreenButCtr,ActiveScreen.CmdButSize):
                    rtn = (WAITCONTROLBUTTON, ActiveScreen.PrevScreen)
                elif ButLayout.InBut(pos,ActiveScreen.NextScreenButCtr,ActiveScreen.CmdButSize):
                    rtn = (WAITCONTROLBUTTON, ActiveScreen.NextScreen)
                else:
                    for i in range(ActiveScreen.ExtraCmdKeys):
                        if ButLayout.InBut(pos, ActiveScreen.ExtraCmdKeysCtr[i], ActiveScreen.CmdButSize):
                            rtn = (WAITEXTRACONTROLBUTTON, i)
                if rtn[0] <> 0:
                    break

            elif event.type == self.MAXTIMEHIT.type:
                self.isDim = True
                config.backlight.ChangeDutyCycle(config.DimLevel)
                pass
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
    
