import displayscreen
from displayscreen import draw_button, draw_cmd_buttons
import pygame
from pygame import gfxdraw
import webcolors
wc = webcolors.name_to_rgb
import config
from config import debugprint, WAITEXTRACONTROLBUTTON, WAITEXIT, WAITNORMALBUTTON, WAITISYCHANGE, dispratio
import screen
import xmltodict
import toucharea

ThermoFont = [None,None,None,None]

def trifromtop(h,v,n,size,c,invert):
    if invert:
        return (h*n,v+size/2,h*n-size/2,v-size/2,h*n+size/2,v-size/2,c)
    else:
        return (h*n,v-size/2,h*n-size/2,v+size/2,h*n+size/2,v+size/2,c)


    
class ThermostatScreenDesc(screen.ScreenDesc):

    def __init__(self, screensection, screenname):
        debugprint(config.dbgscreenbuild, "New ThermostatScreenDesc ",screenname)
        screen.ScreenDesc.__init__(self, screensection, screenname, ())
        self.info = {}

        if ThermoFont[0] == None:
            # initialize on first entry
            ThermoFont[0] = pygame.font.SysFont(None,30,False,False)
            ThermoFont[1] = pygame.font.SysFont(None,50,False,False)
            ThermoFont[2] = pygame.font.SysFont(None,80,False,False)
            ThermoFont[3] = pygame.font.SysFont(None,160,True,False)

        self.charcolor    = screensection.get("CharColor", config.DefaultCharColor)
        self.KColor       = screensection.get("Kcolor",config.Kcolor)
        if screenname not in config.ConnISY.NodeDict:
            print "No such Thermostat: ",screenname
            config.ErrorItems.append("No Thermostat: " + screenname)
        else:
            self.addr = config.ConnISY.NodeDict[screenname].addr
        
        self.TitleRen = ThermoFont[1].render(Screen.FlatenScreenLabel(self.label), 0 , wc(self.charcolor))
        self.TitlePos = ((config.screenwidth - self.TitleRen.get_width())/2, config.topborder)
        self.TempPos  = config.topborder + self.TitleRen.get_height()
        self.StatePos = self.TempPos + ThermoFont[3].get_linesize() - 20
        self.SPPos    = self.StatePos + 25
        self.AdjButSurf = pygame.Surface((320,40))
        self.AdjButTops = self.SPPos + ThermoFont[2].get_linesize() - 5
        centerspacing = config.screenwidth/5
        self.AdjButSurf.fill(wc(self.backcolor))
        arrowsize = 40 * dispratio

        for i in range(4):
            gfxdraw.filled_trigon(self.AdjButSurf,*trifromtop(centerspacing,arrowsize/2,i+1,arrowsize,wc(("red","blue","red","blue")[i]),i%2<>0))
            self.keysbyord.append(toucharea.TouchPoint((centerspacing*(i+1),self.AdjButTops+arrowsize/2),(arrowsize*1.2,arrowsize*1.2)))
        self.ModeButPos = self.AdjButTops + 85 * dispratio 
        
        bsize = (100*dispratio, 50*dispratio)
        self.keysbyord.append(toucharea.ManualKeyDesc("Mode","Mode",(config.screenwidth/4, self.ModeButPos),
                              bsize,self.KColor,self.charcolor,self.charcolor,KOn=config.KOffColor))
        self.keysbyord.append(toucharea.ManualKeyDesc("Fan","Fan",(3*config.screenwidth/4, self.ModeButPos),
                              bsize,self.KColor,self.charcolor,self.charcolor,KOn=config.KOffColor))
        self.ModesPos = self.ModeButPos + bsize[1]/2 + 5* dispratio

    
    def BumpTemp(self,setpoint,degrees):
        
        print "Bump temp: ",setpoint,degrees
        print "New: ",self.info[setpoint][0] + degrees
        config.ConnISY.myisy.conn.request(config.ConnISY.myisy.conn.compileURL(
                ["nodes/",self.addr,"/set/",setpoint,str(self.info[setpoint][0]+degrees)]))
        
    def BumpMode(self,mode, vals):
        print "Bump mode: ",mode, vals
        cv = vals.index(self.info[mode][0])
        print cv, vals[cv]
        cv = (cv+1)%len(vals)
        print "new cv: ",cv
        config.ConnISY.myisy.conn.request(config.ConnISY.myisy.conn.compileURL(
                ["nodes/",self.addr,"/set/",mode,str(vals[cv])]))

    def ShowScreen(self):  

        tstatdict = xmltodict.parse(config.ConnISY.myisy.conn.request(config.ConnISY.myisy.conn.compileURL(["nodes/",self.addr])))
        props = tstatdict["nodeInfo"]["properties"]["property"]
        self.info ={}
        for item in props:
            print item["@id"],":",item["@value"],":",item["@formatted"]
            self.info[item["@id"]] = (int(item['@value']),item['@formatted'])

        config.screen.fill(wc(self.backcolor))
        config.screen.blit(self.TitleRen,self.TitlePos)
        r = ThermoFont[3].render(u"{:4.1f}".format(self.info["ST"][0]/2), 0, wc(self.charcolor))
        config.screen.blit(r,((config.screenwidth - r.get_width())/2, self.TempPos))
        r = ThermoFont[0].render(("Idle","Heating","Cooling")[self.info["CLIHCS"][0]], 0, wc(self.charcolor))
        config.screen.blit(r,((config.screenwidth - r.get_width())/2, self.StatePos))
        r = ThermoFont[2].render("{:2d}    {:2d}".format(self.info["CLISPH"][0]/2,self.info["CLISPC"][0]/2), 0 , wc(self.charcolor))
        config.screen.blit(r,((config.screenwidth - r.get_width())/2, self.SPPos))
        config.screen.blit(self.AdjButSurf,(0,self.AdjButTops))
        draw_button(config.screen, self.keysbyord[4], shrink=True, firstfont=0)
        draw_button(config.screen, self.keysbyord[5], shrink=True, firstfont=0)
        r1 = ThermoFont[1].render(('Off','Heat','Cool','Auto','Fan','Prog Auto','Prog Heat','Prog Cool')[self.info["CLIMD"][0]],0,wc(self.charcolor))
        r2 = ThermoFont[1].render(('On','Auto')[self.info["CLIFS"][0]-7],0,wc(self.charcolor))
        config.screen.blit(r1,(self.keysbyord[4].Center[0]-r1.get_width()/2,self.ModesPos))
        config.screen.blit(r2,(self.keysbyord[5].Center[0]-r2.get_width()/2,self.ModesPos))

        draw_cmd_buttons(config.screen,self)
        pygame.display.update()
    
    def HandleScreen(self,newscr=True):
    
        # stop any watching for device stream
        config.toDaemon.put(["",self.addr])

        self.ShowScreen()

        while 1:
            choice = config.DS.NewWaitPress(self)
            if choice[0] == WAITEXIT:
                return choice[1]
            elif choice[0] == WAITNORMALBUTTON:
                if choice[1] < 4:
                    self.BumpTemp(('CLISPH', 'CLISPH', 'CLISPC', 'CLISPC')[choice[1]], (2, -2, 2, -2)[choice[1]])
                else:
                    self.BumpMode(('CLIMD','CLIFS')[choice[1]-4], (range(8),(7,8))[choice[1]-4])
            elif choice[0] == WAITISYCHANGE:
                print "Thermo change", choice
                self.ShowScreen()



config.screentypes["Thermostat"] = ThermostatScreenDesc