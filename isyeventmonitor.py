import base64
import websocket
import xmltodict
import config
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
import debug
from isycodes import EVENT_CTRL, formatwsitem
import pygame, time
import exitutils
from stores import valuestore
import errno


'''
def CreateWSThread():
	config.EventMonitor = ISYEventMonitor()
	config.QH = threading.Thread(name='QH', target=config.EventMonitor.QHandler)
	config.QH.setDaemon(True)
	config.QH.start()
	logsupport.Logs.Log("ISY stream thread " + str(config.EventMonitor.num) + " started"
'''

class ISYEventMonitor:
	def __init__(self, nm):
		self.hubname = nm
		self.QHnum = 1
		self.a = base64.b64encode((config.ISYuser + ':' + config.ISYpassword).encode('utf-8'))
		self.watchstarttime = time.time()
		self.watchlist = []
		self.streamid = "unset"
		self.seq = 0
		self.lastheartbeat = 0
		self.digestinginput = True
		#self.num = config.QHnum

		self.lasterror = (0,'Init')
		debug.debugPrint('DaemonCtl', "Queue Handler ", self.QHnum, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"]

	def reinit(self):
		self.watchstarttime = time.time()
		self.watchlist = []
		self.seq = 0
		self.QHnum += 1

	def PostStartQHThread(self):
		# todo - should heartbeat logic go here somehow - maybe a proc called back in the daemon code?
		logsupport.Logs.Log("ISY stream thread " + str(self.QHnum) + " setup")
		while self.digestinginput:
			logsupport.Logs.Log("Waiting initial status dump")
			time.sleep(0.5)

	def PreRestartQHThread(self):
		try:
			if self.lasterror[0] == errno.ENETUNREACH:
				# likely home network down so wait a bit
				logsupport.Logs.Log('Wait for likely router reboot or down', severity=ConsoleError)
				# todo overlay a screen delay message so locked up console is understood
				time.sleep(120)
			elif self.lasterror[0] == errno.ETIMEDOUT:
				logsupport.Logs.Log('Timeout on WS - delay to allow possible ISY or router reboot',severity=ConsoleError, tb=False)
				time.sleep(15)
			else:
				logsupport.Logs.Log('Unexpected error on WS stream: ',repr(self.lasterror), severity=ConsoleError, tb=False)
		except Exception as e:
			logsupport.Logs.Log('PreRestartQH internal error ',e)
		self.reinit()

	def QHandler(self):
		def on_error(qws, error):
			logsupport.Logs.Log("Error in WS stream " + str(self.QHnum) + ':' + repr(error), severity=ConsoleError, tb=False)
			self.lasterror = error
			debug.debugPrint('DaemonCtl', "Websocket stream error", self.QHnum, repr(error))
			qws.close()

		# noinspection PyUnusedLocal
		def on_close(qws, code, reason):
			logsupport.Logs.Log("Websocket stream " + str(self.QHnum) + " closed: " + str(code) + ' : ' + str(reason),
							severity=ConsoleError, tb=False)
			debug.debugPrint('DaemonCtl', "Websocket stream closed", str(code), str(reason))

		# noinspection PyUnusedLocal
		def on_open(qws):
			logsupport.Logs.Log("Websocket stream " + str(self.QHnum) + " opened")
			debug.debugPrint('DaemonCtl', "Websocket stream opened: ", self.QHnum, self.streamid)

		# noinspection PyUnusedLocal
		def on_message(qws, message):
			try:
				m = xmltodict.parse(message)
				if debug.dbgStore.GetVal('ISYDump'):
					debug.ISYDump("isystream.dmp", message, pretty=False)

				if 'SubscriptionResponse' in m:
					sr = m['SubscriptionResponse']
					if self.streamid != sr['SID']:
						self.streamid = sr['SID']
						logsupport.Logs.Log("Opened event stream: " + self.streamid, severity=ConsoleWarning)

				elif 'Event' in m:
					E = m['Event']

					esid = E.pop('@sid', 'No sid')
					if self.streamid != esid:
						logsupport.Logs.Log("Unexpected event stream change: " + self.streamid + "/" + str(esid),
										severity=ConsoleError, tb=False)
						exitutils.FatalError("WS Stream ID Changed")

					eseq = int(E.pop('@seqnum', -99))
					if self.seq != eseq:
						logsupport.Logs.Log("Event mismatch - Expected: " + str(self.seq) + " Got: " + str(eseq),
										severity=ConsoleWarning)
						# indicates a missed event - so should rebase the data?
						self.seq = eseq + 1
					else:
						self.seq += 1

					ecode = E.pop('control', 'Missing control')
					if ecode in EVENT_CTRL:
						prcode = EVENT_CTRL[ecode]
					else:
						prcode = "**" + ecode + "**"

					eaction = E.pop('action', 'No action')
					enode = E.pop('node', 'No node')
					eInfo = E.pop('eventInfo', 'No EventInfo')

					if ecode in self.reportablecodes:
						# Node change report
						debug.debugPrint('DaemonStream', time.time() - config.starttime, "Status update in stream: ", eseq, ":",
								   prcode, " : ", enode, " : ", eInfo, " : ", eaction)
						if isinstance(eaction, dict):
							debug.debugPrint('DaemonStream', "V5 stream - pull up action value: ", eaction)
							eaction = eaction["#text"]  # todo the new xmltodict will return as data['action']['#text']

						if enode in config.DS.WatchNodes:
							# alert node changed
							debug.debugPrint('DaemonCtl', 'ISY reports change(alert):', config.ISY.NodesByAddr[enode].name)
							for a in config.DS.WatchNodes[enode]:
								logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
								# noinspection PyArgumentList
								notice = pygame.event.Event(config.DS.ISYAlert, node=enode, value=eaction, alert=a)
								pygame.fastevent.post(notice)

						if config.DS.AS is not None:
							if enode in config.DS.AS.NodeList:
								debug.debugPrint('DaemonCtl', time.time() - config.starttime, "ISY reports node change(screen): ",
										   "Key: ", config.ISY.NodesByAddr[enode].name)
								# noinspection PyArgumentList
								notice = pygame.event.Event(config.DS.ISYChange, node=enode, value=eaction)
								pygame.fastevent.post(notice)

					elif (prcode == 'Trigger') and (eaction == '6'):
						vinfo = eInfo['var']
						vartype = int(vinfo['@type'])
						varid = int(vinfo['@id'])
						varval = int(vinfo['val'])
						debug.debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid,
								   ' set to ', varval)
						valuestore.SetValByAttr('ISY',(vartype,varid),varval, modifier=True)
						'''
						if (vartype, varid) in config.DS.WatchVars.keys():
							config.DS.WatchVarVals[vartype, varid] = varval
							if vartype == 1:
								debug.debugPrint('DaemonCtl', 'Int var change(alert): ', config.ISY.varsIntInv[varid], ' <- ',
										   varval)
							elif vartype == 2:
								debug.debugPrint('DaemonCtl', 'State var change(alert): ', config.ISY.varsStateInv[varid], ' <- ',
										   varval)
							else:
								logsupport.Logs.Log('Bad var message:' + str(varid), severity=ConsoleError)

							for a in config.DS.WatchVars[(vartype, varid)]:
								logsupport.Logs.Log("Var alert fired: " + str(a))
								notice = pygame.event.Event(config.DS.ISYVar, node=(vartype, varid), value=varval,
															alert=a)
								pygame.fastevent.post(notice)
						

						if config.DS.AS is not None:
							if (vartype, varid) in config.DS.AS.VarsList:
								if vartype == 1:
									debug.debugPrint('DaemonCtl', 'Int var change(screen): ', config.ISY.varsIntInv[varid],
											   ' <- ', varval)
								elif vartype == 2:
									debug.debugPrint('DaemonCtl', 'State var change(screen): ', config.ISY.varsStateInv[varid],
											   ' <- ',
											   varval)
								notice = pygame.event.Event(config.DS.ISYChange, vartype=vartype, varid=varid, value=varval)
								pygame.fastevent.post(notice)
						'''

					elif prcode == 'Heartbeat':
						self.lastheartbeat = time.time()
						self.digestinginput = False
					elif prcode == 'Billing':
						self.digestinginput = False
					else:
						pass  # handle any other?
					efmtact = E.pop('fmtAct', 'v4stream')
					if E:
						logsupport.Logs.Log("Extra info in event: " + str(ecode) +'/' + str(prcode) +'/' + str(eaction) +'/' + str(enode) +'/' + str(eInfo) + str(E), severity=ConsoleWarning)
					debug.debugPrint('DaemonStream', time.time() - config.starttime,
									 formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, E))

					if ecode == "ERR":
						try:
							isynd = config.ISY.NodesByAddr[enode].name
						except (KeyError, AttributeError):
							isynd = enode
						logsupport.Logs.Log("ISY shows comm error for node: " + str(isynd), severity=ConsoleWarning)

					if ecode == 'ST':
						if enode == "20 51 B2 1":
							print("Off Ceil Set: " + str(eaction))
						if int(eaction) < 0:
							print("Strange node set: "+str(enode)+' '+str(eaction))
						config.ISY.NodesByAddr[enode].devState = int(eaction)

				else:
					logsupport.Logs.Log("Strange item in event stream: " + str(m), severity=ConsoleWarning)
			except Exception as E:
				print(E)
				logsupport.Logs.Log("Exception in QH on message: ", E)


		#websocket.enableTrace(True)
		websocket.setdefaulttimeout(30)
		if config.ISYaddr.startswith('http://'):
			wsurl = 'ws://' + config.ISYaddr[7:] + '/rest/subscribe'
		elif config.ISYaddr.startswith('https://'):
			wsurl = 'wss://' + config.ISYaddr[8:] + '/rest/subscribe'
		else:
			wsurl = 'ws://' + config.ISYaddr + '/rest/subscribe'
		while True:
			try:
				ws = websocket.WebSocketApp(wsurl, on_message=on_message,
										on_error=on_error,
										on_close=on_close, on_open=on_open,
										subprotocols=['ISYSUB'], header={'Authorization': 'Basic ' + self.a.decode('ascii')})
				break
			except AttributeError as e:
				logsupport.Logs.Log("Problem starting WS handler - retrying: ",repr(e))
				print(e)
		self.digestinginput = True
		self.lastheartbeat = time.time()
		ws.run_forever()
		logsupport.Logs.Log("QH Thread " + str(self.QHnum) + " exiting", severity=ConsoleError)

