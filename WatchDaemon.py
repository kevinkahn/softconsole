import sys
import os
import time
import config
from config import debugprint
import LogSupport

from  ISY.IsyEvent import ISYEvent
from  ISY.IsyEventData import EVENT_CTRL


def event_feed(*arg):

    if time.time() < config.starttime+10:
        debugprint(config.dbgdaemon,time.time(),"Skipping")
        return None
    
    while not config.toDaemon.empty():
        msg = config.toDaemon.get()
        if len(msg) == 0:
            config.watchlist = ["empty"]
        else:
            config.watchlist = config.toDaemon.get()
        debugprint(config.dbgdaemon,time.time(), "New watchlist: ",config.watchlist)

    data = arg[0]
    
    eventcode = data["control"]
    if eventcode in EVENT_CTRL:
        prcode = EVENT_CTRL[eventcode]
    else:
        prcode = "***"+eventcode+"***"

    if (prcode == config.watchlist[0] or config.watchlist[0] == "") and data["node"] in config.watchlist:
        debugprint(config.dbgdaemon,time.time(),"Status update in stream: ",data["Event-seqnum"],":",eventcode," : ",data["node"]," : ",data["eventInfo"]," : ",data["action"]," : ",data["Event-sid"])
        config.fromDaemon.put((data["node"],data["action"]))
    else:
        debugprint(config.dbgdaemon,time.time(),"Unmatched update in stream: ",data["Event-seqnum"],":",eventcode," : ",data["node"]," : ",data["eventInfo"]," : ",data["action"]," : ",data["Event-sid"])

def Watcher():
    
    config.starttime = time.time()
    config.watchlist = []
    debugprint(config.dbgdaemon, "Watcher: ", config.starttime, os.getpid())
    server = ISYEvent()
    server.subscribe(addr=config.ISYaddr, userl=config.ISYuser, userp=config.ISYpassword)
    server.set_process_func(event_feed, "")
    
    server.events_loop()
