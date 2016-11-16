import os
import time

# For now import private bug fixed version
# from  ISY.IsyEvent import ISYEvent
from IsyEvent import ISYEvent
from  ISY.IsyEventData import EVENT_CTRL

import config
from config import debugPrint
from logsupport import ConsoleWarning

seq = 0

def event_feed(*arg):
	reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS", "CLIMD",
					   "CLIHUM", "CLIHCS", "BRT", "DIM"]
	global seq
	seq = seq + 1
	data = arg[0]
	if config.seq <> int(data["Event-seqnum"]):
		config.fromDaemon.put(
			("Log", "Event mismatch - Expected: " + str(config.seq) + " Got: " + str(data["Event-seqnum"]), ConsoleWarning))
		config.seq = int(data["Event-seqnum"]) + 1
	else:
		config.seq += 1

	if config.streamid <> data["Event-sid"]:
		config.fromDaemon.put(("Log", "Now using event stream: " + str(data["Event-sid"]), ConsoleWarning))
		config.streamid = data["Event-sid"]

	if time.time() < config.watchstarttime + 5:
		debugPrint('DaemonStream', time.time(), "Skipping item in stream: ", data["Event-seqnum"], ":",
				   data["control"], " : ", data["node"], " : ", data["eventInfo"], " : ", data["action"])
		return None

	while not config.toDaemon.empty():
		msg = config.toDaemon.get()
		if len(msg) == 0:
			config.watchlist = ["empty"]
		elif msg[0] == 'flagchange':
			config.Flags[msg[1]] = msg[2]
		else:
			config.watchlist = msg
		debugPrint('DaemonCtl', time.time(), "New watchlist(watcher): ", config.watchlist)

	data = arg[0]
	# data["Event-seqnum"],":",prcode," : ",data["node"]," : ",data["eventInfo"]," : ",data["action"]," : ",data["Event-sid"])



	eventcode = data["control"]
	if eventcode in EVENT_CTRL:
		prcode = EVENT_CTRL[eventcode]
	# print "Orig EC", eventcode, prcode
	else:
		prcode = "**" + eventcode + "**"
	# print "Ugly EC", eventcode, prcode
	if (eventcode in reportablecodes or config.watchlist[0] == "") and data["node"] in config.watchlist:
		debugPrint('DaemonCtl', time.time(), "Status update in stream: ", data["Event-seqnum"], ":", prcode, " : ",
				   data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('DaemonStream', time.time(), "Raw stream item: ", data)
		if data["action"] is dict:
			data["action"] = data["action"]["action"]
			debugPrint('DaemonStream', "V5 stream - pull up action value: ", data["action"])
		config.fromDaemon.put(("Node", data["node"], data["action"], seq))
		debugPrint('DaemonCtl', "Qsize at daemon ", config.fromDaemon.qsize())
	else:
		config.debugPrint('DaemonStream', time.time(), "Other  update in stream: ", data["Event-seqnum"], ":", prcode,
						  " : ",
						  data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('DaemonStream', time.time(), "Raw stream item: ", data)

def Watcher():
	config.watchstarttime = time.time()
	config.watchlist = ['init']
	debugPrint('DaemonCtl', "Watcher: ", config.watchstarttime, os.getpid())
	config.Daemon_pid = os.getpid()
	server = ISYEvent()  # can add parameter debug = 3 to have library dump some info out output
	server.subscribe(addr=config.ISYaddr, userl=config.ISYuser, userp=config.ISYpassword)
	server.set_process_func(event_feed, "")

	server.events_loop()
