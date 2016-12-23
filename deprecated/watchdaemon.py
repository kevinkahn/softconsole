import os
import time

# For now import private bug fixed version
# from  ISY.IsyEvent import ISYEvent
import debug
from IsyEvent import ISYEvent
from  ISY.IsyEventData import EVENT_CTRL

import config
from debug import debugPrint
from logsupport import ConsoleWarning

seq = 0
reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS", "CLIMD",
				   "CLIHUM", "CLIHCS", "BRT", "DIM"]
watchlist = []
varlist = []
streamid = ''
watchstarttime = 0


def event_feed(*arg):
	global seq, reportablecodes, watchlist, varlist, streamid, watchstarttime
	data = arg[0]
	if seq <> int(data["Event-seqnum"]):
		config.fromDaemon.put(
			("Log", "Event mismatch - Expected: " + str(seq) + " Got: " + str(data["Event-seqnum"]), ConsoleWarning))
		seq = int(data["Event-seqnum"]) + 1
	else:
		seq += 1

	if streamid <> data["Event-sid"]:
		config.fromDaemon.put(("Log", "Now using event stream: " + str(data["Event-sid"]), ConsoleWarning))
		streamid = data["Event-sid"]
	"""
	if time.time() < watchstarttime + 2:
		debugPrint('DaemonStream', time.time(), "Skipping item in stream: ", data["Event-seqnum"], ":",
				   data["control"], " : ", data["node"], " : ", data["eventInfo"], " : ", data["action"])
		return None
	"""

	while not config.toDaemon.empty():
		msg = config.toDaemon.get()
		if len(msg) == 0:
			debugPrint('DaemonCtl', 'Empty message from console: ')
		elif msg[0] == 'flagchange':
			debug.Flags[msg[1]] = msg[2]
		elif msg[0] == 'Status':
			watchlist = msg[1:]
			debugPrint('DaemonCtl', time.time(), "New watchlist(watcher): ", watchlist)
		elif msg[0] == 'Vars':
			varlist = msg[1:]
			debugPrint('DaemonCtl', "New varlist(watcher): ", varlist)
		else:
			debugPrint('DaemonCtl', 'Bad message from console: ', msg)


	data = arg[0]
	# data["Event-seqnum"],":",prcode," : ",data["node"]," : ",data["eventInfo"]," : ",data["action"]," : ",data["Event-sid"])



	eventcode = data["control"]
	if eventcode in EVENT_CTRL:
		prcode = EVENT_CTRL[eventcode]
	else:
		prcode = "**" + eventcode + "**"

	if (eventcode in reportablecodes) and data["node"] in watchlist:
		debugPrint('DaemonCtl', time.time(), "Status update in stream: ", data["Event-seqnum"], ":", prcode, " : ",
				   data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('DaemonStream', time.time(), "Raw stream item: ", data)
		if data["action"] is dict:
			data["action"] = data["action"]["action"]  # todo the new xmltodict will return as data['action']['#text']
			debugPrint('DaemonStream', "V5 stream - pull up action value: ", data["action"])
		config.fromDaemon.put(("Node", data["node"], data["action"], seq))
		debugPrint('DaemonCtl', "Qsize at daemon ", config.fromDaemon.qsize())
	elif (eventcode == '_1') and (data['action'] == '6'):
		vinfo = data['eventInfo']['var']
		vartype = int(vinfo['var-type'])
		varid = int(vinfo['var-id'])
		varval = int(vinfo['val'])
		debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid, ' set to ',
				   varval)
		if (vartype, varid) in varlist:
			config.fromDaemon.put(("VarChg", vartype, varid, varval))
			debugPrint('DaemonCtl', 'Qsize at daemon', config.fromDaemon.qsize(), ' VarChg:', vartype, ':', varid, ':',
					   varval)
	else:
		debug.debugPrint('DaemonStream', time.time(), "Other  update in stream: ", data["Event-seqnum"], ":", prcode,
						  " : ",
						 data["node"], " : ", data["eventInfo"], " : ", data["action"])
		debugPrint('DaemonStream', time.time(), "Raw stream item: ", data)

def Watcher():
	global watchlist, varlist
	watchstarttime = time.time()
	watchlist = []
	varlist = []
	debugPrint('DaemonCtl', "Watcher: ", watchstarttime, os.getpid())
	config.Daemon_pid = os.getpid()
	server = ISYEvent()  # can add parameter debug = 3 to have library dump some info out output
	server.subscribe(addr=config.ISYaddr, userl=config.ISYuser, userp=config.ISYpassword)
	server.set_process_func(event_feed, "")

	server.events_loop()
