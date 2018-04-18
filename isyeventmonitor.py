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


class ISYEMInternalError(Exception):
	pass

class ISYEventMonitor(object):


	def __init__(self, thisISY):
		self.isy = thisISY
		self.hubname = thisISY.name
		self.QHnum = 1
		self.a = base64.b64encode((self.isy.user + ':' + self.isy.password).encode('utf-8'))
		self.watchstarttime = time.time()
		self.watchlist = []
		self.streamid = "unset"
		self.seq = 0
		self.lastheartbeat = 0
		self.hbcount = 0
		self.digestinginput = True
		self.AlertNodes = {}

		self.lasterror = (0,'Init')
		debug.debugPrint('DaemonCtl', "Queue Handler ", self.QHnum, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"] # "RR", "OL",

	def reinit(self):
		self.watchstarttime = time.time()
		self.watchlist = []
		self.seq = 0
		self.QHnum += 1

	def PostStartQHThread(self):
		logsupport.Logs.Log("ISY stream thread " + str(self.QHnum) + " setup")
		while self.digestinginput:
			logsupport.Logs.Log("Waiting initial status dump")
			time.sleep(0.5)
		logsupport.Logs.Log("ISY initial status streamed ", self.seq, " items")

	def PreRestartQHThread(self):
		try:
			if self.lasterror == TimeoutError:
				logsupport.Logs.Log('(TimeoutError) Wait for likely router reboot or down', severity=ConsoleError)
				time.sleep(120)
			if self.lasterror[0] == errno.ENETUNREACH:
				# likely home network down so wait a bit
				logsupport.Logs.Log('(NETUNREACH) Wait for likely router reboot or down', severity=ConsoleError)
				# todo overlay a screen delay message so locked up console is understood
				time.sleep(120)
			elif self.lasterror[0] == errno.ETIMEDOUT:
				logsupport.Logs.Log('(errno TIMEOUT) Timeout on WS - delay to allow possible ISY or router reboot',severity=ConsoleError, tb=False)
				logsupport.Logs.Log('Original error report: '+repr(self.lasterror))
				time.sleep(15)
				# todo - bug in websocket that results in attribute error for errno.WSEACONNECTIONREFUSED check
			else:
				logsupport.Logs.Log('Unexpected error on WS stream: ',repr(self.lasterror), severity=ConsoleError, tb=False)
		except Exception as e:
			logsupport.Logs.Log('PreRestartQH internal error ',e)
		self.reinit()

	def _NormalizeState(self,stateval):
		t = stateval
		try:
			if isinstance(stateval, unicode):
				t = str(stateval)
		except:
			pass
		if isinstance(t, str):
			return int(t) if t.isdigit() else 0
		return t

	def QHandler(self):
		def on_error(qws, error):
			logsupport.Logs.Log("Error in WS stream " + str(self.QHnum) + ':' + repr(error), severity=ConsoleError, tb=False)
			try:
				if error == TimeoutError: # Py3
					error = (errno.ETIMEDOUT,"Converted Py3 Timeout")
			except:
				pass
			try:
				if error == AttributeError: # Py2 websocket debug todo
					error = (errno.ETIMEDOUT,"Websock bug catch")
			except:
				pass
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
						raise ISYEMInternalError
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

						if enode in self.AlertNodes:
							# alert node changed
							debug.debugPrint('DaemonCtl', 'ISY reports change(alert):', self.isy.NodesByAddr[enode].name)
							for a in self.AlertNodes[enode]:
								logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
								# noinspection PyArgumentList
								notice = pygame.event.Event(config.DS.ISYAlert, node=enode, value=self._NormalizeState(eaction), alert=a)
								pygame.fastevent.post(notice)

						if enode in self.isy.NodesByAddr:
							N = self.isy.NodesByAddr[enode]
							devstate = self._NormalizeState(eaction) # N.devState =
							print(N.name+' set to '+str(devstate)+' was '+str(N.devState)) # todo activate this full state approach

						if config.DS.AS is not None:
							if self.isy.name in config.DS.AS.HubInterestList:
								if enode in config.DS.AS.HubInterestList[self.isy.name]:
										debug.debugPrint('DaemonCtl', time.time() - config.starttime, "ISY reports node change(screen): ",
												   "Key: ", self.isy.NodesByAddr[enode].name)
										# noinspection PyArgumentList
										notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.isy.name, node=enode, value=self._NormalizeState(eaction))
										pygame.fastevent.post(notice)

					elif (prcode == 'Trigger') and (eaction == '6'):
						vinfo = eInfo['var']
						vartype = int(vinfo['@type'])
						varid = int(vinfo['@id'])
						varval = int(vinfo['val'])
						debug.debugPrint('DaemonCtl', 'Var change: ', valuestore.GetNameFromAttr(self.hubname,(vartype,varid)),' set to ', varval)
						debug.debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid,
								   ' set to ', varval)
						valuestore.SetValByAttr(self.hubname,(vartype,varid),varval, modifier=True)

					elif prcode == 'Heartbeat':
						if self.hbcount > 0:
							# wait 2 heartbeats
							self.digestinginput = False
						self.lastheartbeat = time.time()
						self.hbcount += 1
					elif prcode == 'Billing':
						self.digestinginput = False
					else:
						pass  # handle any other?
					efmtact = E.pop('fmtAct', 'v4stream')
					if E:
						logsupport.Logs.Log("Extra info in event: " + str(ecode) +'/' + str(prcode) +'/' + str(eaction) +'/' + str(enode) +'/' + str(eInfo) + str(E), severity=ConsoleWarning)
					debug.debugPrint('DaemonStream', time.time() - config.starttime,
									 formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, E, self.isy))

					if ecode == "ERR":
						try:
							isynd = self.isy.NodesByAddr[enode].name
						except (KeyError, AttributeError):
							isynd = enode
						logsupport.Logs.Log("ISY shows comm error for node: " + str(isynd), severity=ConsoleWarning)

					if ecode == 'ST':
						if int(eaction) < 0:
							print("Strange node set: "+str(enode)+' '+str(eaction))
						node = self.isy.NodesByAddr[enode]
						debug.debugPrint('ISYchg', 'ISY Node: ', node.name, ' state change from: ', node.devState,
										 ' to: ', int(eaction))
						node.devState = int(eaction)

				else:
					logsupport.Logs.Log("Strange item in event stream: " + str(m), severity=ConsoleWarning)
			except Exception as E:
				print(E)
				logsupport.Logs.Log("Exception in QH on message: ", E)


		#websocket.enableTrace(True)
		websocket.setdefaulttimeout(30)
		if self.isy.addr.startswith('http://'):
			wsurl = 'ws://' + self.isy.addr[7:] + '/rest/subscribe'
		elif self.isy.addr.startswith('https://'):
			wsurl = 'wss://' + self.isy.addr[8:] + '/rest/subscribe'
		else:
			wsurl = 'ws://' +self.isy.addr + '/rest/subscribe'
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

