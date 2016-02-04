import os
import config
import pygame
import webcolors
import TouchArea
import time
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITEXIT, WAITISYCHANGE, WAITEXTRACONTROLBUTTON
import LogSupport
from LogSupport import Info, Warning, Error



wc = webcolors.name_to_rgb


def draw_cmd_buttons(scr,AS):
    draw_button(scr,AS.PrevScreenKey)
    draw_button(scr,AS.NextScreenKey)
    for K in AS.ExtraCmdKeys:
        draw_button(scr,K)

def draw_button(screen, Key, shrink=True, firstfont=0):

    lines = len(Key.label)
    buttonsmaller = (Key.Size[0] - 6, Key.Size[1] - 6)
    x = Key.Center[0] - Key.Size[0]/2
    y = Key.Center[1] - Key.Size[1]/2

    HiColor = Key.KOnColor if Key.State else Key.KOffColor
    pygame.draw.rect(screen, wc(Key.backcolor), ((x,y), Key.Size), 0)
    pygame.draw.rect(screen, wc(HiColor), ((x+3,y+3), buttonsmaller), 3)
    s = pygame.Surface(Key.Size)
    s.set_alpha(150)
    s.fill(wc("white"))
    
    if not Key.State:
        screen.blit(s, (x,y))
    # compute writeable area for text
    textarea = (buttonsmaller[0]-6,buttonsmaller[1]-1)
    fontchoice = firstfont
    if shrink:
        for l in range(lines):
            for i in range(fontchoice,len(TouchArea.ButtonFonts)):
                txtsize = TouchArea.ButtonFonts[fontchoice].size(Key.label[l])
                if lines*txtsize[1] >= textarea[1] or txtsize[0] >= textarea[0]:
                    fontchoice = i
                    
    for i in range(lines) :
        #ren = pygame.transform.rotate(dispscreen.MyFont.render(txt[i], 0, HiColor), 0)
        ren = TouchArea.ButtonFonts[fontchoice].render(Key.label[i], 0, wc(HiColor))
        vert_off = ((i+1)*Key.Size[1]/(1+lines)) - ren.get_height()/2
        horiz_off = (Key.Size[0] - ren.get_width())/2
        screen.blit(ren,(x+horiz_off, y+vert_off))
        
    pygame.display.update()
    

class DisplayScreen:
    screen = None

    
    def __init__(self):

        #self.screen = config.screen

        print "Screensize: ",config.screenwidth, config.screenheight
        config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))

        # define user events
        self.MAXTIMEHIT = pygame.event.Event(pygame.USEREVENT)
        self.INTERVALHIT = pygame.event.Event(pygame.USEREVENT+1)
        self.GOHOMEHIT = pygame.event.Event(pygame.USEREVENT+2)
        self.isDim = False
        
        self.presscount = 0

  
   

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
                time.sleep(.01)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = (pygame.mouse.get_pos()[0],pygame.mouse.get_pos()[1])
                if self.presscount < 10:
                    print pos
                    self.presscount += 1
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
                    rtn = (WAITEXIT, tapcount)
                    break
                # on any touch reset return to home screen
                pygame.time.set_timer(self.GOHOMEHIT.type, int(config.HomeScreenTO)*1000)
                # on any touch restart dim timer and reset to bright if dim
                pygame.time.set_timer(self.MAXTIMEHIT.type, config.DimTO*1000)
                if self.isDim:
                    config.backlight.ChangeDutyCycle(config.BrightLevel)
                    self.isDim = False
                    continue  # touch that ends dim screen is otherwise ignored
                
                print "Pos: ",pos
                for i in range(len(ActiveScreen.keysbyord)):
                    K = ActiveScreen.keysbyord[i]
                    print K.Center, K.Size
                    if TouchArea.InBut(pos, K):
                        rtn = (WAITNORMALBUTTON, i)
                if TouchArea.InBut(pos,ActiveScreen.PrevScreenKey):
                    rtn = (WAITEXIT, ActiveScreen.PrevScreen)
                elif TouchArea.InBut(pos,ActiveScreen.NextScreenKey):
                    rtn = (WAITEXIT, ActiveScreen.NextScreen)
                else:
                    for K in ActiveScreen.ExtraCmdKeys:
                        if TouchArea.InBut(pos, K):
                            rtn = (WAITEXTRACONTROLBUTTON, K.name)
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
                rtn = (WAITEXIT,config.HomeScreen)
                break
            else:
                pass # ignore and flush other events
            
        pygame.time.set_timer(self.INTERVALHIT.type, 0)
        pygame.time.set_timer(self.MAXTIMEHIT.type, 0)
        
        return rtn
    
