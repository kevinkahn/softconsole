import base64
import websocket
import xmltodict
import config
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail, ConsoleDetailHigh
import debug
from isycodes import EVENT_CTRL, formatwsitem
import pygame, time
import exitutils
from stores import valuestore
import errno
import isycodes
from threadmanager import ThreadStartException

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
		self.AlertNodes = {}
		self.delayedstart = 0
		self.WS = None
		self.THstate = 'init'

		self.lasterror = (0,'Init')
		debug.debugPrint('DaemonCtl', "Queue Handler ", self.QHnum, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"] # "RR", "OL",

	def EndWSServer(self):
		self.WS.close()

	def FakeNodeChange(self):
		# noinspection PyArgumentList
		notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.isy.name, node=None, value=-1)
		pygame.fastevent.post(notice)

	def reinit(self):
		self.watchstarttime = time.time()
		self.watchlist = []
		self.seq = 0
		self.hbcount = 0
		self.QHnum += 1

	def PostStartQHThread(self):
		hungcount = 40
		while self.THstate == 'restarting':
			logsupport.Logs.Log("Waiting ISY thread start")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0: raise ThreadStartException
		while self.THstate == 'delaying':
			time.sleep(1)
		hungcount = 60
		while self.THstate == 'starting':
			logsupport.Logs.Log("Waiting initial status dump")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0: raise ThreadStartException
		if self.THstate == 'running':
			self.isy._HubOnline = True
			logsupport.Logs.Log("ISY initial status streamed ", self.seq, " items")
			self.isy.Vars.CheckValsUpToDate(reload=True)
			logsupport.Logs.Log("ISY vars updated")
		elif self.THstate == 'failed':
			logsupport.Logs.Log("Failed ISY Restart", severity=ConsoleWarning)
		else:
			logsupport.Logs.Log("Unknown ISY QH Thread state")

	def PreRestartQHThread(self):
		self.isy._HubOnline = False
		self.THstate = 'restarting'
		try:
			# noinspection PyBroadException
			try:
				if isinstance(self.lasterror, TimeoutError):
					logsupport.Logs.Log('(TimeoutError) Wait for likely router reboot or down', severity=ConsoleError, tb=False)
					self.delayedstart = 63
					self.reinit()
					return
			except:
				pass # TimeoutError is Python 3 specific
			if isinstance(self.lasterror, OSError):
				logsupport.Logs.Log('ISY Thread Lasterror was: ', repr(self.lasterror), severity=ConsoleError)
				self.delayedstart = 62
			elif isinstance(self.lasterror, websocket.WebSocketConnectionClosedException):
				logsupport.Logs.Log('ISY Thread websocket closed unexpectedly', repr(self.lasterror),
									severity=ConsoleError, tb=False)
				self.delayedstart = 30  # brief delay - ISY may be doing query or otherwise busy
			elif self.lasterror[0] == errno.ENETUNREACH:
				# likely home network down so wait a bit
				logsupport.Logs.Log('(NETUNREACH) Wait for likely router reboot or down', severity=ConsoleError, tb=False)
				# todo overlay a screen delay message so locked up console is understood
				self.delayedstart = 121
			elif self.lasterror[0] == errno.ETIMEDOUT:
				logsupport.Logs.Log('(errno TIMEOUT) Timeout on WS - delay to allow possible ISY or router reboot',severity=ConsoleError, tb=False)
				self.delayedstart = 61
				# todo - bug in websocket that results in attribute error for errno.WSEACONNECTIONREFUSED check
			elif self.lasterror == (0, 'Init'):
				logsupport.Logs.Log('QHThead failed to start - comms likely out')
				self.delayedstart = 60
			else:
				logsupport.Logs.Log('Unexpected error on WS stream: ',repr(self.lasterror), severity=ConsoleError, tb=False)
		except Exception as e:
			logsupport.Logs.Log('PreRestartQH internal error ',e)
		self.reinit()

	def QHandler(self):
		def on_error(qws, error):
			logsupport.Logs.Log("Error in WS stream " + str(self.QHnum) + ':' + repr(error), severity=ConsoleError, tb=False)
			# noinspection PyBroadException
			try:
				if error.args[0] == 'timed out':
					error = (errno.ETIMEDOUT,'InitTimedOut')
			except:
				pass
			# noinspection PyBroadException
			try:
				if error == TimeoutError: # Py3
					error = (errno.ETIMEDOUT,"Converted Py3 Timeout")
			except:
				pass
			# noinspection PyBroadException
			try:
				if error == AttributeError: # Py2 websocket debug todo
					error = (errno.ETIMEDOUT,"Websock bug catch")
			except:
				pass
			self.lasterror = error
			self.THstate = 'failed'
			debug.debugPrint('DaemonCtl', "Websocket stream error", self.QHnum, repr(error))
			try:
				if error[0] != errno.ETIMEDOUT:
					logsupport.Logs.Log("Error in WS stream " + str(self.QHnum) + ':' + repr(error),
										severity=ConsoleError,
										tb=False)
				else:
					logsupport.Logs.Log("Timeout on ISY WS stream", severity=ConsoleError, tb=False)
			except:
				logsupport.Logs.Log("Unindexable error: ", repr(error), severity=ConsoleError, tb=False)
			qws.close()

		# noinspection PyUnusedLocal
		def on_close(qws, code, reason):
			logsupport.Logs.Log("Websocket stream " + str(self.QHnum) + " closed: " + str(code) + ' : ' + str(reason),
							severity=ConsoleError, tb=False)
			debug.debugPrint('DaemonCtl', "Websocket stream closed", str(code), str(reason))

		def on_open(qws):
			self.THstate = 'starting'
			logsupport.Logs.Log("Websocket stream " + str(self.QHnum) + " opened")
			debug.debugPrint('DaemonCtl', "Websocket stream opened: ", self.QHnum, self.streamid)
			self.WS = qws

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
						logsupport.Logs.Log("Opened event stream: " + self.streamid)

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

					if isinstance(eaction, dict):
						debug.debugPrint('DaemonStream', "V5 stream - pull up action value: ", eaction)
						eaction = eaction["#text"]  # todo the new xmltodict will return as data['action']['#text']

					if ecode == 'ST':  # update cached state first before posting alerts or race
						if enode in self.isy.NodesByAddr:
							N = self.isy.NodesByAddr[enode]
							oldstate = N.devState
							N.devState = isycodes._NormalizeState(eaction)
							debug.debugPrint('ISYchg', 'ISY Node: ', N.name, ' state change from: ', oldstate,
											 ' to: ', N.devState)
							if (oldstate == N.devState) and self.THstate == 'running':
								logsupport.Logs.Log(
									"ISY State report with no change: " + N.name + ' state: ' + str(oldstate),
									severity=ConsoleWarning)
							else:
								logsupport.Logs.Log(
									"Status change for " + N.name + '(' + str(enode) + ') to ' + str(N.devState),
									severity=ConsoleDetailHigh)
								# status changed to post to any alerts that want it
								# since alerts can only react to the state of a node we check only on an ST message
								# screens on the other hand may need to know about other actions (thermostat e.g.)
								# so they get checked below under reportablecodes
								# if I check alerts there I get extra invocations for the DON and DOF e.g. which while not
								# harmful are anomolous
								if enode in self.AlertNodes:
									# alert node changed
									debug.debugPrint('DaemonCtl', 'ISY reports change(alert):',
													 self.isy.NodesByAddr[enode].name)
									for a in self.AlertNodes[enode]:
										if self.THstate != 'running':
											# this is a restart or initial dump so indicate upwards to avoid misleading log entry
											if a.state == 'Armed':
												a.state == 'Init'
										logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
										# noinspection PyArgumentList
										notice = pygame.event.Event(config.DS.ISYAlert,  hub=self.isy.name, node=enode,
																	value=isycodes._NormalizeState(eaction), alert=a)
										pygame.fastevent.post(notice)

					if ecode in self.reportablecodes:
						# Node change report
						debug.debugPrint('DaemonStream', time.time() - config.starttime, "Status update in stream: ", eseq, ":",
								   prcode, " : ", enode, " : ", eInfo, " : ", eaction)

						# logsupport.Logs.Log('reportable event '+str(ecode)+' for '+str(enode)+' action '+str(eaction))

						if config.DS.AS is not None:
							if self.isy.name in config.DS.AS.HubInterestList:
								if enode in config.DS.AS.HubInterestList[self.isy.name]:
										debug.debugPrint('DaemonCtl', time.time() - config.starttime, "ISY reports node change(screen): ",
												   "Key: ", self.isy.NodesByAddr[enode].name)
										# noinspection PyArgumentList
										notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.isy.name, node=enode, value=isycodes._NormalizeState(eaction))
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
							self.THstate = 'running'
						self.lastheartbeat = time.time()
						self.hbcount += 1
					elif prcode == 'Billing':
						self.THstate = 'running'
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


				else:
					logsupport.Logs.Log("Strange item in event stream: " + str(m), severity=ConsoleWarning)
			except Exception as E:
				print(E)
				logsupport.Logs.Log("Exception in QH on message: ", E)

		self.THstate = 'delaying'
		logsupport.Logs.Log("ISY stream thread " + str(self.QHnum) + " setup")
		if self.delayedstart != 0:
			logsupport.Logs.Log("Delaying ISY Hub restart for probable network reset: ",str(self.delayedstart),' seconds')
			time.sleep(self.delayedstart)
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
				# noinspection PyArgumentList
				ws = websocket.WebSocketApp(wsurl, on_message=on_message,
										on_error=on_error,
										on_close=on_close, on_open=on_open,
										subprotocols=['ISYSUB'], header={'Authorization': 'Basic ' + self.a.decode('ascii')})
				break
			except AttributeError as e:
				logsupport.Logs.Log("Problem starting WS handler - retrying: ",repr(e))
				print(e)
		self.lastheartbeat = time.time()
		ws.run_forever(ping_timeout=999)
		self.THstate = 'failed'
		self.isy._HubOnline = False
		logsupport.Logs.Log("ISY QH Thread " + str(self.QHnum) + " exiting", severity=ConsoleError, tb=False)
