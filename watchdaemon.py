import os
import time

from  ISY.IsyEvent import ISYEvent
from  ISY.IsyEventData import EVENT_CTRL

import config
from config import debugPrint
from logsupport import ConsoleWarning


def event_feed(*arg):
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

	if time.time() < config.watchstarttime + 10:
		debugPrint('Daemon', time.time(), "Skipping item in stream: ", data["Event-seqnum"], ":",
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
		debugPrint('Daemon', time.time(), "New watchlist: ", config.watchlist)

	data = arg[0]
	# data["Event-seqnum"],":",prcode," : ",data["node"]," : ",data["eventInfo"]," : ",data["action"]," : ",data["Event-sid"])



	eventcode = data["control"]
	if eventcode in EVENT_CTRL:
		prcode = EVENT_CTRL[eventcode]
	# print "Orig EC", eventcode, prcode
	else:
		prcode = "**" + eventcode + "**"
	# print "Ugly EC", eventcode, prcode
	if (prcode == "Status" or config.watchlist[0] == "") and data["node"] in config.watchlist:
		debugPrint('Daemon', time.time(), "Status update in stream: ", data["Event-seqnum"], ":", prcode, " : ",
				   data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('Daemon', time.time(), "Raw stream item: ", data)
		config.fromDaemon.put(("Node", data["node"], data["action"]))
		debugPrint('Daemon', "Qsize at daemon ", config.fromDaemon.qsize())
	else:
		config.debugPrint('Daemon', time.time(), "Other  update in stream: ", data["Event-seqnum"], ":", prcode, " : ",
						  data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('Daemon', time.time(), "Raw stream item: ", data)

def Watcher():
	config.watchstarttime = time.time()
	config.watchlist = ['init']
	debugPrint('Daemon', "Watcher: ", config.watchstarttime, os.getpid())
	server = ISYEvent(debug=3)
	server.subscribe(addr=config.ISYaddr, userl=config.ISYuser, userp=config.ISYpassword)
	server.set_process_func(event_feed, "")

	server.events_loop()
