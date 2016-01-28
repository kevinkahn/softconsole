import PyISY
import pygame
import config
from config import isytreewalkdbgprt as dbgprt
from config import debugprint as debugprint
import time
from xml.dom import minidom

def get_real_time_status(nodeaddr):
    xml = config.ConnISY.myisy.conn.request(config.ConnISY.myisy.conn.compileURL(["status/",nodeaddr]))
    # turn xml into a DOM get its property element
    propertyelement = minidom.parseString(xml).getElementsByTagName("property")
    nowstate = -1
    for i in range(propertyelement.length):
        realreturnval = propertyelement.item(i).attributes # this should have items id =ST and value=status cheating and not checking ST
        for j in range(realreturnval.length):
            item = realreturnval.item(j)
            # just grab the value items "value"
            if item.name == "value":
                nowstate = int(item.value)
    if nowstate <> -1:
        return nowstate
    else:
        # LOG an error and report the xml
        return 0

class NodeItem():
    
    def __init__(self,t,n,a,nd):
        self.typ = t
        self.name = n
        self.addr = a
        self.obj = nd
        
class SceneItem():
    
    def __init__(self,t,n,a,p,nd,m):
        self.typ = t
        self.name = n
        self.addr = a
        self.proxy = p
        self.obj = nd
        self.members = m
        


class ISYsetup():
    

    MasterDict={}
    NodeDict={}
    SceneDict={}
    Dups=[]
    ProgramDict={}

    def EnumeratePrograms(self,id):
        for i in id.children:
            if i[0] == "folder":
                debugprint(dbgprt, "Program Folder: ", i[1])
                self.EnumeratePrograms(self.myisy.programs[i[2]])
            elif i[0] == "program":
                self.ProgramDict[i[1]] = self.myisy.programs[i[2]]
                debugprint(dbgprt, "Program: ", i[1], self.ProgramDict[i[1]])
            else:
                debugprint(dbgprt, "Unknown item: ",i[0], i[1])


    def WalkFolder(self,id):  # id is a Node Manager Class
        
        debugprint(dbgprt, "Children item: ", id.children)
        for node in id.children:
            debugprint(dbgprt, "Node: ", node)
#            entry = (node[0],node[1],node[2],self.myisy.nodes[node[2]])
            if node[0] == "group" and node[1] == "~Auto DR":
                # special case the weird ISY item
                debugprint(dbgprt, "Discard Auto DR")
            elif node[0] == "folder":
                debugprint(dbgprt,"Folder:  ", node[1], " with address ", node[2])
                self.WalkFolder(self.myisy.nodes[node[2]])
            elif node[0] == 'group':
                debugprint(dbgprt, "Scene:   ", node[1], " with address ", node[2])
                if node[1] in self.MasterDict:
                    debugprint(dbgprt, "Duplicate node/scene name when finding scene:", node[1])
                    self.Dups.append(node)
                g = id.getByID(node[2])
                debugprint(dbgprt, "Scene ",node[1]," includes ", g.members, " default proxying with ", g.members[0])
                SI = SceneItem(node[0],node[1],node[2],g.members[0],g,g.members)
                self.MasterDict[node[1]]=SI # overwrite entry if there since then it's a node and we prefer scenes
                self.SceneDict[node[1]]=SI
               
            elif node[0] == 'node':
                debugprint(dbgprt, "Node:    ", node[1], " with address ", node[2])
                N = NodeItem(node[0],node[1],node[2],id.getByID(node[2]))
                if node[1] in self.MasterDict:
                    debugprint(dbgprt, "Duplicate node/scene name when finding node:", node[1])
                    self.Dups.append(node)
                else:
                    self.MasterDict[node[1]]=N  # leave scene in MasterDict if it's already there
                self.NodeDict[node[1]]=N
            else:
                debugprint(dbgprt, "ISY Walk Error ", node)
    
    def __init__(self):
        self.i = 1
        self.myisy = PyISY.ISY(config.ISYaddr,80,config.ISYuser,config.ISYpassword) 
        
        
