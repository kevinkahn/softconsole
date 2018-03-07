import base64
import websocket
import xmltodict
import config
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from debug import debugPrint
import debug
from isycodes import EVENT_CTRL, formatwsitem
import pygame, time
import exitutils
import threading


def CreateWSThread():
	config.EventMonitor = ISYEventMonitor()
	config.QH = threading.Thread(name='QH', target=config.EventMonitor.QHandler)
	config.QH.setDaemon(True)
	config.QH.start()
	config.Logs.Log("ISY stream thread " + str(config.EventMonitor.num) + " started")

class ISYEventMonitor:
	def __init__(self):
		self.a = base64.b64encode(config.ISYuser + ':' + config.ISYpassword)
		self.watchstarttime = time.time()
		self.watchlist = []
		self.varlist = []
		self.streamid = "unset"
		self.seq = 0
		self.num = config.QHnum
		config.QHnum += 1
		self.lasterror = (0,'Init')
		debugPrint('DaemonCtl', "Queue Handler ", self.num, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"]

	def QHandler(self):
		def on_error(ws, error):
			config.Logs.Log("Error in WS stream " + str(self.num) + ':' + repr(error), severity=ConsoleError, tb=False) #todo sometimes do the tb?
			self.lasterror = error
			debugPrint('DaemonCtl', "Websocket stream error", self.num, repr(error))
			ws.close()

		# exitutils.FatalError("websocket stream error")

		def on_close(ws, code, reason):
			config.Logs.Log("Websocket stream " + str(self.num) + " closed: " + str(code) + ' : ' + str(reason),
							severity=ConsoleError,
							tb=False)
			debugPrint('DaemonCtl', "Websocket stream closed", str(code), str(reason))

		def on_open(ws):
			config.Logs.Log("Websocket stream " + str(self.num) + " opened")
			debugPrint('DaemonCtl', "Websocket stream opened: ", self.num, self.streamid)

		def on_message(ws, message):
			m = xmltodict.parse(message)
			if debug.Flags['ISYDump']:
				debug.ISYDump("isystream.dmp", message, pretty=False)

			if 'SubscriptionResponse' in m:
				sr = m['SubscriptionResponse']
				if self.streamid <> sr['SID']:
					self.streamid = sr['SID']
					config.Logs.Log("Opened event stream: " + self.streamid, severity=ConsoleWarning)

			elif 'Event' in m:
				e = m['Event']

				esid = e.pop('@sid', 'No sid')
				if self.streamid <> esid:
					config.Logs.Log("Unexpected event stream change: " + self.streamid + "/" + str(esid),
									severity=ConsoleError, tb=False)
					exitutils.FatalError("WS Stream ID Changed")

				eseq = int(e.pop('@seqnum', -99))
				if self.seq <> eseq:
					config.Logs.Log("Event mismatch - Expected: " + str(self.seq) + " Got: " + str(eseq),
									severity=ConsoleWarning)
					# indicates a missed event - so should rebase the data?
					self.seq = eseq + 1
				else:
					self.seq += 1

				ecode = e.pop('control', 'Missing control')
				if ecode in EVENT_CTRL:
					prcode = EVENT_CTRL[ecode]
				else:
					prcode = "**" + ecode + "**"

				eaction = e.pop('action', 'No action')
				enode = e.pop('node', 'No node')
				eInfo = e.pop('eventInfo', 'No EventInfo')

				if ecode in self.reportablecodes:
					# Node change report
					debugPrint('DaemonStream', time.time() - config.starttime, "Status update in stream: ", eseq, ":",
							   prcode, " : ", enode, " : ", eInfo, " : ", eaction)
					if isinstance(eaction, dict):
						debugPrint('DaemonStream', "V5 stream - pull up action value: ", eaction)
						eaction = eaction["#text"]  # todo the new xmltodict will return as data['action']['#text']

					if enode in config.DS.WatchNodes:
						# alert node changed
						debugPrint('DaemonCtl', 'ISY reports change(alert):', config.ISY.NodesByAddr[enode].name)
						for a in config.DS.WatchNodes[enode]:
							config.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
							notice = pygame.event.Event(config.DS.ISYAlert, node=enode, value=eaction, alert=a)
							pygame.fastevent.post(notice)

					if config.DS.AS is not None:
						if enode in config.DS.AS.NodeList:
							debugPrint('DaemonCtl', time.time() - config.starttime, "ISY reports node change(screen): ",
									   "Key: ", config.ISY.NodesByAddr[enode].name)
							notice = pygame.event.Event(config.DS.ISYChange, node=enode, value=eaction)
							pygame.fastevent.post(notice)

				elif (prcode == 'Trigger') and (eaction == '6'):
					vinfo = eInfo['var']
					vartype = int(vinfo['@type'])
					varid = int(vinfo['@id'])
					varval = int(vinfo['val'])
					debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid,
							   ' set to ', varval)
					if (vartype, varid) in config.DS.WatchVars.keys():
						config.DS.WatchVarVals[vartype, varid] = varval
						if vartype == 1:
							debugPrint('DaemonCtl', 'Int var change(alert): ', config.ISY.varsIntInv[varid], ' <- ',
									   varval)
						elif vartype == 2:
							debugPrint('DaemonCtl', 'State var change(alert): ', config.ISY.varsStateInv[varid], ' <- ',
									   varval)
						else:
							config.Logs.Log('Bad var message:' + str(varid), severity=ConsoleError)

						for a in config.DS.WatchVars[(vartype, varid)]:
							config.Logs.Log("Var alert fired: " + str(a))
							notice = pygame.event.Event(config.DS.ISYVar, node=(vartype, varid), value=varval,
														alert=a)
							pygame.fastevent.post(notice)

					if config.DS.AS is not None:
						if (vartype, varid) in config.DS.AS.VarsList:
							if vartype == 1:
								debugPrint('DaemonCtl', 'Int var change(screen): ', config.ISY.varsIntInv[varid],
										   ' <- ', varval)
							elif vartype == 2:
								debugPrint('DaemonCtl', 'State var change(screen): ', config.ISY.varsStateInv[varid],
										   ' <- ',
										   varval)
							notice = pygame.event.Event(config.DS.ISYChange, vartype=vartype, varid=varid, value=varval)
							pygame.fastevent.post(notice)

				elif prcode == 'Heartbeat':
					config.lastheartbeat = time.time()
					config.digestinginit = False
				elif prcode == 'Billing':
					config.digestinginit = False
				else:
					pass  # handle any other? todo
				if e:
					config.Logs.Log("Extra info in event: "+str(ecode)+'/'+str(prcode)+'/'+str(eaction)+'/'+str(enode)+'/'+str(eInfo) + str(e), severity=ConsoleWarning)
				debugPrint('DaemonStream', time.time() - config.starttime,
						   formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, e))
#				if enode == '20 F9 76 1':
#					debugPrint('DebugSpecial', time.time() - config.starttime,
#							   formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, e))
				if ecode == "ERR":
					try:
						isynd = config.ISY.NodesByAddr[enode].name
					except:
						isynd = enode
					config.Logs.Log("ISY shows comm error for node: " + str(isynd), severity=ConsoleWarning)

				if ecode == 'ST':
					config.ISY.NodesByAddr[enode].devState = int(eaction)

			else:
				config.Logs.Log("Strange item in event stream: " + str(m), severity=ConsoleWarning)

		# websocket.enableTrace(True)
		if config.ISYaddr != '':
			websocket.setdefaulttimeout(240)
			if config.ISYaddr.startswith('http://'):
				wsurl = 'ws://' + config.ISYaddr[7:] + '/rest/subscribe'
			elif config.ISYaddr.startswith('https://'):
				wsurl = 'wss://' + config.ISYaddr[8:] + '/rest/subscribe'
			else:
				wsurl = 'ws://' + config.ISYaddr + '/rest/subscribe'
			ws = websocket.WebSocketApp(wsurl, on_message=on_message,
										on_error=on_error,
										on_close=on_close, on_open=on_open,
										subprotocols=['ISYSUB'], header={'Authorization': 'Basic ' + self.a})
			config.lastheartbeat = time.time()
			ws.run_forever()
			config.Logs.Log("QH Thread " + str(self.num) + " exiting", severity=ConsoleError)
		else:
			config.Logs.Log("No ISY to talk to",severity=ConsoleWarning)
