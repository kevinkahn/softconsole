import base64
import websocket
import xmltodict
import config
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from debug import debugPrint, Flags
from isycodes import EVENT_CTRL, formatwsitem
import pygame, time
import exitutils


class ISYEventMonitor:
	def __init__(self):
		self.a = base64.b64encode(config.ISYuser + ':' + config.ISYpassword)
		self.watchstarttime = time.time()
		self.watchlist = []
		self.varlist = []
		self.streamid = "unset"
		self.seq = 0
		debugPrint('DaemonCtl', "Watcher: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"]

	def QHandler(self):
		def on_error(ws, error):
			config.Logs.Log("Error in WS stream " + repr(error), severity=ConsoleError)
			exitutils.FatalError("websocket stream error")

		def on_close(ws):
			debugPrint('DaemonCtl', "Websocket stream closed")

		def on_open(ws):
			debugPrint('DaemonCtl', "Websocket stream opened: " + self.streamid)

		def on_message(ws, message):
			global varlist, watchlist
			m = xmltodict.parse(message)

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
									severity=ConsoleError)
					exitutils.FatalError("WS Stream ID Changed")

				eseq = int(e.pop('@seqnum', -99))
				if self.seq <> eseq:
					config.Logs.Log("Event mismatch - Expected: " + str(self.seq) + " Got: " + str(eseq),
									severity=ConsoleWarning)
					# todo indicates a missed event - so should rebase the data?
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
				if config.DS.AS is not None:
					tt = config.DS.AS.NodeWatch + config.DS.WatchNodes.keys()
				else:
					tt = config.DS.WatchNodes.keys()
				if (ecode in self.reportablecodes) and (enode in tt):
					debugPrint('DaemonCtl', time.time(), "Status update in stream: ", eseq, ":", prcode, " : ", enode,
							   " : ", eInfo, " : ", eaction)
					if eaction is dict:
						debugPrint('DaemonStream', "V5 stream - pull up action value: ", eaction)
						eaction = eaction["#text"]  # todo the new xmltodict will return as data['action']['#text']

					if enode in config.DS.WatchNodes:
						debugPrint('DaemonCtl', 'ISY reports change(alert):', config.ISY.NodesByAddr[enode].name)
						for a in config.DS.WatchNodes[enode]:
							config.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
							notice = pygame.event.Event(config.DS.ISYAlert, node=enode, value=eaction, alert=a)
							pygame.fastevent.post(notice)
					else:  # don't explicity test for config.DS.AS.Nodewatch since AS may not be active yet
						debugPrint('DaemonCtl', time.time(), "ISY reports change: ", "Key: ",
								   config.ISY.NodesByAddr[enode].name)
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
							debugPrint('DaemonCtl', 'Int var change: ', config.ISY.varsIntInv[varid], ' <- ', varval)
						elif vartype == 2:
							debugPrint('DaemonCtl', 'State var change: ', config.ISY.varsStateInv[varid], ' <- ',
									   varval)
						else:
							config.Logs.Log('Bad var message:' + str(varid), severity=ConsoleError)

						for a in config.DS.WatchVars[(vartype, varid)]:
							config.Logs.Log("Var alert fired: " + str(a))
							notice = pygame.event.Event(config.DS.ISYVar, vartype=vartype, varid=varid, value=varval,
														alert=a)
							pygame.fastevent.post(notice)

				else:
					pass  # handle any other? todo

				if e:
					config.Logs.Log("Extra info in event: " + str(e), severity=ConsoleWarning)
				debugPrint('DaemonStream', time.time(), formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, e))

				if ecode == 'ST':
					config.ISY.NodesByAddr[enode].devState = int(eaction)

			else:
				config.Logs.Log("Strange item in event stream: " + str(m), severity=ConsoleWarning)

		websocket.enableTrace(True)
		ws = websocket.WebSocketApp('ws://' + config.ISYaddr + '/rest/subscribe', on_message=on_message,
									on_error=on_error,
									on_close=on_close, on_open=on_open,
									subprotocols=['ISYSUB'], header={'Authorization': 'Basic ' + self.a})
		ws.run_forever()
