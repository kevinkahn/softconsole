import ISYSetup
import DisplayScreen
import webcolors
import config
import functools
import time
from config import *
wc = webcolors.name_to_rgb
import Screen
import pywapi

class WeatherScreenDesc(Screen.ScreenDesc):
    # Describes a Clock Screen: name, background, dimtimeout, charcolor, (lineformat 3 tuple), fontsize)
    
    def __init__(self, sname, sbkg, lab, schar, oformat, cfs):
        self.charcolor = schar
        placename = ""
        placeid = ??  lookup = pywapi.get_location_ids(placename)
        #self.lineformat = oformat
        self.fontsize = int(cfs)
        Screen.ScreenDesc.__init__(self,sname,sbkg, lab)
        
    def __repr__(self):
        return Screen.ScreenDesc.__repr__(self)+"\r\n     WeatherScreenDesc:"+str(self.charcolor)+":"+str(self.lineformat)+":"+str(self.fontsize)

    def HandleScreen(self,newscr=True):
    
        isDim = False
        config.screen.screen.fill(wc(self.backcolor))
        
        
        weather_result = pywapi.get_weather_from_weather_com(location_id)
        
"""
        def repaintClock(cycle):
            # param ignored for clock
            usefulheight = config.screenheight - config.topborder - config.botborder
            h = 0
            l = []
            ClkFont = pygame.font.SysFont(None,self.fontsize,True,True)
            for i in range(len(self.lineformat)):
                l.append(ClkFont.render(time.strftime(self.lineformat[i]), 0, wc(self.charcolor)))
                h = h + l[i].get_height()
            s = (usefulheight - h)/len(l)
        
            config.screen.screen.fill(wc(self.backcolor),pygame.Rect(0,0,config.screenwidth,config.screenheight-config.botborder))
            for i in range(len(l)):
                vert_off = config.topborder + (i+1)*s + l[i].get_height()/2
                horiz_off = (config.screenwidth - l[i].get_width())/2
                config.screen.screen.blit(l[i],(horiz_off, vert_off))
            pygame.display.update()
"""            
        repaintClock(0)
        
        DisplayScreen.draw_cmd_buttons(config.screen,self)
        
        resetH = True
        while 1:
"""
            choice = config.screen.NewWaitPress(self, 10, callbackproc=repaintClock, callbackint=.5, resetHome = resetH)
            resetH = False
            if not DisplayScreen.dim_change(choice):
                if choice[0] == WAITCONTROLBUTTON:
                    resetH = True
                    break
                elif choice[0] == WAITISYCHANGE:
                    pass 
                elif choice[0] == WAITGOHOME:
                    return  config.HomeScreen
            else:
                if not config.isDim:
                    resetH = True
"""
        return choice[1]

import urllib2
import json
f = urllib2.urlopen('http://api.wunderground.com/api/47dc922e667b69a1/geolookup/conditions/q/IA/Cedar_Rapids.json')
json_string = f.read()
parsed_json = json.loads(json_string)
location = parsed_json['location']['city']
temp_f = parsed_json['current_observation']['temp_f']
print "Current temperature in %s is: %s" % (location, temp_f)
f.close()
        