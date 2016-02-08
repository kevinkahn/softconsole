import displayscreen
import pygame
import webcolors
import config
from config import debugprint, WAITEXTRACONTROLBUTTON, WAITEXIT
import time
wc = webcolors.name_to_rgb
import screen
import urllib2
import json
import logsupport
import functools
from datetime import timedelta

WeathFont = [None,None,None]

def hms_string(sec_elapsed):
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = int(sec_elapsed % 60)
    return "{}:{:>02d}:{:>02d}".format(h, m, s)

def TreeDict(d,*args):
    # Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
    if len(args) == 1:
        temp = d[args[0]]
        if isinstance(temp, basestring) and temp.isdigit():
            temp = int(temp)
        else:
            try:
                temp = float(temp)
            except (ValueError, TypeError):
                pass

        return temp
    else:
        return TreeDict(d[args[0]],*args[1:])

def RenderScreenLines(recipe,extracter,color):
    h = 0
    renderedlines = []
    centered = []
    for line in recipe:
        if isinstance(line[3], basestring):
            linestr = line[2].format(d=line[3])
        else:
            args = []
            #print line, format
            for item in line[3]:
                args.append(extracter(*item))
                #print args, type(args[-1]).__name__
            if len(args) == 1 and isinstance(args[0], basestring):
                #print "One arg: ",type(args[0]).__name__,args
                linestr = line[2].format(d=args[0])
            else:
                #for x in args:
                #   print "Mult arg: ",type(x).__name__,x,args
                linestr = line[2].format(d=args)
                #print line[2].format(d=args)
        r = WeathFont[line[0]].render(linestr,0,wc(color))
        renderedlines.append(r)
        centered.append(line[1])
        h = h + r.get_height()
    return (renderedlines,centered,h)

    
class WeatherScreenDesc(screen.ScreenDesc):

    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New WeatherScreenDesc ",screenname)
        
        if WeathFont[0] == None:
            # initialize on first entry
            WeathFont[0] = pygame.font.SysFont(None,20,False,False)
            WeathFont[1] = pygame.font.SysFont(None,30,True,False)
            WeathFont[2] = pygame.font.SysFont(None,45,True,True)

        self.wunderkey = screensection.get("wunderkey","NoKeySupplied")
        self.location = screensection.get("location","")
        screen.ScreenDesc.__init__(self, screensection, screenname, ('which',))
        self.charcolor    = screensection.get("CharCol", config.DefaultCharColor)
        self.lastwebreq = 0 # time of last call out to wunderground
        self.url = 'http://api.wunderground.com/api/' + self.wunderkey + '/geolookup/conditions/forecast/astronomy/q/' + self.location + '.json'
        self.parsed_json = {}
        self.scrlabel =""
        for s in self.label:
            self.scrlabel = self.scrlabel + " " + s
        self.conditions = [(2,True,"{d}",self.scrlabel),
                           (1,True,"{d}",(('location','city'),)),
                           (1,False,u"Currently: {d[0]} {d[1]}\u00B0F",(('current_observation','weather'),('current_observation','temp_f'))),
                           (0, False, u"  Feels like: {d[0]}\u00B0", (('current_observation', 'feelslike_f'),)),
                           (1,False,"Wind {d[0]} at {d[1]} gusts {d[2]}",(('current_observation','wind_dir'),('current_observation','wind_mph'),('current_observation','wind_gust_mph'))),
                           (1,False,"Sunrise: {d[0]:02d}:{d[1]:02d}",(('sun_phase','sunrise','hour'),('sun_phase','sunrise','minute'))),
                           (1,False,"Sunset:  {d[0]:02d}:{d[1]:02d}",(('sun_phase','sunset','hour'),('sun_phase','sunset','minute'))),
                           (0,False,"Moon rise: {d[0]:02d}:{d[1]:02d}  set: {d[2]:02d}:{d[3]:02d}",(('moon_phase','moonrise','hour'),('moon_phase','moonrise','minute'),
                                                                                   ('moon_phase','moonset','hour'),('moon_phase','moonset','minute'))),
                           (0,False,"     {d[0]}% illuminated",(('moon_phase','percentIlluminated'),)),
                           (0,False,"will be replaced","")]
        self.forecast    = [(1,False,u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}",(('date','weekday_short'),('high','fahrenheit'),('low','fahrenheit'),('conditions',))),
                            (1,False,"Wind: {d[0]} at {d[1]}",(('avewind','dir'),('avewind','mph')))]

                           
        
        

    def __repr__(self):
        return screen.ScreenDesc.__repr__(self) + "\r\n     WeatherScreenDesc:" + str(self.charcolor) + ":" + str(self.lineformat) + ":" + str(self.fontsize)

    

    def ShowScreen(self,conditions):
        config.screen.fill(wc(self.backcolor))
        usefulheight = config.screenheight - config.topborder - config.botborder
        renderedlines = []
        h = 0
        centered = []

        if conditions:
            age = hms_string(time.time() - int(self.js('current_observation', 'observation_epoch')))
            self.conditions[-1] = (0, False, "Readings as of {d} ago", age)
            self.SetExtraCmdTitles([('Forecast',)])
            renderedlines, centered, h = RenderScreenLines(self.conditions, self.js, self.charcolor)
        else:
            self.SetExtraCmdTitles([('Conditions',)])
            renderedlines.append(WeathFont[2].render(self.scrlabel, 0, wc(self.charcolor)))
            centered.append(True)
            h = h + renderedlines[0].get_height()
            for fcst in self.fcsts:
                fs = functools.partial(TreeDict, fcst)
                r, c, temph = RenderScreenLines(self.forecast, fs, self.charcolor)
                h = h + temph
                renderedlines = renderedlines + r
                centered = centered + c

        s = (usefulheight - h)/(len(renderedlines) - 1)
        vert_off = config.topborder

        for i in range(len(renderedlines)):
            if centered[i]:
                horiz_off = (config.screenwidth - renderedlines[i].get_width())/2
            else:
                horiz_off = config.horizborder
            config.screen.blit(renderedlines[i],(horiz_off, vert_off))
            vert_off = vert_off + renderedlines[i].get_height() + s
        displayscreen.draw_cmd_buttons(config.screen, self)
        pygame.display.update()
    
    def HandleScreen(self,newscr=True):
    
        # stop any watching for device stream
        config.toDaemon.put([])
        
        currentconditions = True

        if time.time() > self.lastwebreq + 5*60:
            # refresh the conditions - don't do more than once per 5 minutes
            f = urllib2.urlopen(self.url)
            val = f.read()
            if val.find("keynotfound") <> -1:
                config.Logs.Log("Bad weatherunderground key:" + self.name, logsupport.Error)
                return config.HomeScreen
            self.lastwebreq = time.time()
            self.parsed_json = json.loads(val)

            self.js = functools.partial(TreeDict,self.parsed_json)
            self.fcsts = TreeDict(self.parsed_json,'forecast','simpleforecast','forecastday')
            f.close()
        self.ShowScreen(currentconditions)        
        
        while 1:
            choice = config.DS.NewWaitPress(self)
            if choice[0] == WAITEXIT:
                return choice[1]
            elif choice[0] == WAITEXTRACONTROLBUTTON:
                currentconditions = not currentconditions
                self.ShowScreen(currentconditions)

config.screentypes["Weather"] = WeatherScreenDesc