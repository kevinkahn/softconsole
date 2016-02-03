import DisplayScreen
from DisplayScreen import draw_button
import pygame
from pygame import gfxdraw
import webcolors
import config
from config import debugprint, WAITEXTRACONTROLBUTTON, WAITEXIT, WAITNORMALBUTTON
import time
wc = webcolors.name_to_rgb
import Screen
import urllib2
import xmltodict
import json
import functools
import KeyScreen
from datetime import timedelta
from configobj import Section

ThermoFont = [None,None,None]

def trifromtop(h,v,n,size,c,invert):
    if invert:
        return (h*n,v+size/2,h*n-size/2,v-size/2,h*n+size/2,v-size/2,c)
    else:
        return (h*n,v-size/2,h*n-size/2,v+size/2,h*n+size/2,v+size/2,c)


def ShowScreen(label,color, info, AS):
    screenpos = config.topborder
    scrlabel = ""
    for s in label:
        scrlabel = scrlabel + " " + s
    r = ThermoFont[0].render(scrlabel, 0 , wc(color))
    config.screen.screen.blit(r,((config.screenwidth - r.get_width())/2, screenpos))
    screenpos = screenpos + r.get_height() # scale pixels to display
        
    r = ThermoFont[2].render(u"{:4.1f}".format(info["ST"][0]/2), 0, wc(color))
    config.screen.screen.blit(r,((config.screenwidth - r.get_width())/2, screenpos))
    screenpos = screenpos + r.get_height()-20 # scale pixels to display
    
    if info["CLIHCS"][0] == 1:
        r = ThermoFont[0].render("Heating", 0, wc(color))
    elif info["CLIHCS"][0] == 2:
        r = ThermoFont[0].render("Cooling", 0, wc(color))
    else:
        r = ThermoFont[0].render("Idle", 0, wc(color))
    config.screen.screen.blit(r,((config.screenwidth - r.get_width())/2, screenpos))
    screenpos = screenpos + 20
    
    r = ThermoFont[1].render("{:2d}    {:2d}".format(info["CLISPH"][0]/2,info["CLISPC"][0]/2), 0 , wc(color))
    config.screen.screen.blit(r,((config.screenwidth - r.get_width())/2, screenpos))
    screenpos = screenpos + r.get_height() + 20 # scale pixels to display
    
    centerspacing = config.screenwidth/5
    
    gfxdraw.filled_trigon(config.screen.screen,*trifromtop(centerspacing,screenpos,1,40,wc("red"),False))
    gfxdraw.filled_trigon(config.screen.screen,*trifromtop(centerspacing,screenpos,2,40,wc("blue"),True))    
    gfxdraw.filled_trigon(config.screen.screen,*trifromtop(centerspacing,screenpos,3,40,wc("red"),False))
    gfxdraw.filled_trigon(config.screen.screen,*trifromtop(centerspacing,screenpos,4,40,wc("blue"),True))
    for i in range(4):
        AS.keysbyord.append(str(i))
        AS.keys[str(i)] = KeyScreen.TouchPoint((centerspacing*(i+1),screenpos),(40,40))
    screenpos = screenpos + 60 # scale pixels
    
    bsize = (120, 50)
    centerspacing = config.screenwidth/3
    AS.keysbyord.append("mode")
    AS.keysbyord.append("fan")
    modectr = (centerspacing, screenpos)
    fanctr = (centerspacing*2, screenpos)
    
    AS.keys["mode"] = KeyScreen.ManualKeyDesc(("Mode",),modectr,bsize,"beige",wc(color))
    AS.keys["fan"] = KeyScreen.ManualKeyDesc(("Fan",),fanctr,bsize,"beige",wc(color))
    
    draw_button(config.screen, AS.keys["mode"].label, "green", True, modectr, bsize, shrink=False, firstfont=3)
    draw_button(config.screen, AS.keys["fan"].label, "green", True, fanctr, bsize, shrink=False, firstfont=3)

    return screenpos+30
    
class ThermostatScreenDesc(Screen.ScreenDesc):

    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New ThermostatScreenDesc ",screenname)
        Screen.ScreenDesc.__init__(self, screensection, screenname, 0)
        self.NumKeys = 6
        self.keysbyord = []
        self.keys = {}
        

        if ThermoFont[0] == None:
            # initialize on first entry
            ThermoFont[0] = pygame.font.SysFont(None,30,False,False)
            ThermoFont[1] = pygame.font.SysFont(None,80,False,False)
            ThermoFont[2] = pygame.font.SysFont(None,160,True,False)


        self.charcolor    = screensection.get("CharColor",config.CharColor)
        if screenname not in config.ConnISY.NodeDict:
            print "No such Thermostat: ",screenname
            config.ErrorItems.append("No Thermostat: " + screenname)
        else:
            self.addr = config.ConnISY.NodeDict[screenname].addr
        self.thermdisplay = [(0,False,"Fan : {d}","CLIFS"),


                           (0,False,"Mode: {d}","CLIMD")]


        
    
    def HandleScreen(self,newscr=True):
    
        # stop any watching for device stream
        config.toDaemon.put([])
        xml = config.ConnISY.myisy.conn.request(config.ConnISY.myisy.conn.compileURL(["nodes/",self.addr]))

        tstatdict = xmltodict.parse(xml)
        props = tstatdict["nodeInfo"]["properties"]["property"]
        screeninfo ={}
        for item in props:
            print item["@id"],":",item["@value"],":",item["@formatted"]
            screeninfo[item["@id"]] = (int(item['@value']),item['@formatted'])

        config.screen.screen.fill(wc(self.backcolor))
        
        t = ShowScreen(self.label, self.charcolor, screeninfo, self)
        usefulheight = config.screenheight - t - config.botborder
        h = 0
        renderedlines = []
        centered = []
        
        for line in self.thermdisplay:
            linestr = line[2].format(d=screeninfo[line[3]][0])
            print linestr
            #print line, format
            r = ThermoFont[line[0]].render(linestr,0,wc(self.charcolor))
            renderedlines.append(r)
            centered.append(line[1])
            h = h + r.get_height()
        
        s = (usefulheight - h)/(len(renderedlines)-1)
        vert_off = t
        for i in range(len(renderedlines)):
            if centered[i]:
                horiz_off = (config.screenwidth - renderedlines[i].get_width())/2
            else:
                horiz_off = config.horizborder
            config.screen.screen.blit(renderedlines[i],(horiz_off, vert_off))
            vert_off = vert_off + renderedlines[i].get_height() + s
        DisplayScreen.draw_cmd_buttons(config.screen,self)    
        pygame.display.update()
        
        while 1:
            choice = config.screen.NewWaitPress(self)
            if choice[0] == WAITEXIT:
                return choice[1]
            elif choice[0] == WAITNORMALBUTTON:
                print "Tap: ",choice[1]



config.screentypes["Thermostat"] = ThermostatScreenDesc