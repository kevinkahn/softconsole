import base64
import websocket
import xmltodict
import config
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail, ConsoleDetailHigh
import debug
from isycodes import EVENT_CTRL, formatwsitem
import time
import exitutils
from controlevents import *
from stores import valuestore
import errno
import isycodes
from threadmanager import ThreadStartException
import threading

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
		self.querycnt = 0
		self.queryqueued = {}

		self.lasterror = 'Init'
		debug.debugPrint('DaemonCtl', "Queue Handler ", self.QHnum, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"] # "RR", "OL",

	def EndWSServer(self):
		self.lasterror = "DirectCommError"
		self.WS.close()

	def RealQuery(self, enode, seq):
		logsupport.Logs.Log("Queued query attempt for: " + enode)
		time.sleep(120)  # allow any in progress query at ISY a chance to clear
		if enode not in self.isy.ErrNodes:
			logsupport.Logs.Log("Node error cleared without need of query for: " + enode)
			return
		logsupport.Logs.Log(self.hubname + ": Attempt query (" + str(seq) + ") in errored node: " + enode,
							severity=ConsoleWarning)
		r = self.isy.try_ISY_comm('query/' + enode, timeout=120, closeonfail=False)
		if r == '':
			logsupport.Logs.Log(self.hubname + ": Query (" + str(seq) + ") attempt failed for node: " + enode,
								severity=ConsoleWarning)
		else:
			logsupport.Logs.Log(self.hubname + ": Query (" + str(seq) + ") attempt succeeded for node: " + enode)
		del self.isy.ErrNodes[enode]
		del self.queryqueued[enode]

	def DoNodeQuery(self, enode):
		if enode not in self.queryqueued:
			self.querycnt += 1
			self.queryqueued[enode] = self.querycnt
			t = threading.Thread(name='Query-' + str(self.querycnt) + '-' + enode, target=self.RealQuery, daemon=True,
							 args=(enode, self.querycnt))
			t.start()
		else:
			logsupport.Logs.Log(
				self.hubname + ": Query " + str(self.queryqueued[enode]) + " already queued for node: " + enode)

	def FakeNodeChange(self):
		# noinspection PyArgumentList
		PostControl(HubNodeChange, hub=self.isy.name, node=None, value=-1)

	def reinit(self):
		self.watchstarttime = time.time()
		self.watchlist = []
		self.seq = 0
		self.hbcount = 0
		self.QHnum += 1

	def PostStartQHThread(self):
		hungcount = 40
		while self.THstate == 'restarting':
			logsupport.Logs.Log(self.hubname + " Waiting thread start")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0: raise ThreadStartException
		while self.THstate == 'delaying':
			time.sleep(1)
		hungcount = 60
		while self.THstate == 'starting':
			logsupport.Logs.Log(self.hubname + " Waiting initial status dump")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0: raise ThreadStartException
		if self.THstate == 'running':
			self.isy._HubOnline = True
			logsupport.Logs.Log(self.hubname + " initial status streamed ", self.seq, " items")
			self.isy.Vars.CheckValsUpToDate(reload=True)
			logsupport.Logs.Log(self.hubname + " vars updated")
		elif self.THstate == 'failed':
			logsupport.Logs.Log(self.hubname + " Failed Thread Restart", severity=ConsoleWarning)
		else:
			logsupport.Logs.Log(self.hubname + " Unknown ISY QH Thread state")

	def PreRestartQHThread(self):
		self.isy._HubOnline = False
		self.THstate = 'restarting'
		try:
			if self.lasterror == 'ISYSocketTimeOut':
				logsupport.Logs.Log(self.hubname + '(TimeoutError) Wait for likely router reboot or down',
									severity=ConsoleWarning, tb=False)
				self.delayedstart = 150
				self.reinit()
				return

			if self.lasterror == 'ISYWSTimeOut':
				logsupport.Logs.Log(self.hubname + ' WS restart after surprise close - short delay (15)',
									severity=ConsoleWarning)
				self.delayedstart = 15
			elif self.lasterror == 'ISYNetDown':
				# likely home network down so wait a bit
				logsupport.Logs.Log(self.hubname + ' WS restart for NETUNREACH - delay likely router reboot or down',
									severity=ConsoleWarning)
				# todo overlay a screen delay message so locked up console is understood
				self.delayedstart = 121
			elif self.lasterror == 'ISYClose':
				logsupport.Logs.Log(self.hubname + ' Recovering closed WS stream')
				self.delayedstart = 2
				# todo - bug in websocket that results in attribute error for errno.WSEACONNECTIONREFUSED check ??
			elif self.lasterror == 'DirectCommError':
				logsupport.Logs.Log(self.hubname + ' WS restart because of failed direct communication failure')
				self.delayedstart = 90  # probably ISY doing query
			else:
				logsupport.Logs.Log(self.hubname + ' Unexpected error on WS stream: ', self.lasterror,
									severity=ConsoleError, tb=False)
				self.delayedstart = 90
		except Exception as e:
			logsupport.Logs.Log(self.hubname + ' PreRestartQH internal error ', e)
		self.reinit()

	def QHandler(self):
		def on_error(qws, error):
			self.isy.HBWS.Entry(repr(error))
			self.lasterror = "ISYUnknown"
			if isinstance(error, websocket.WebSocketConnectionClosedException):
				logsupport.Logs.Log(self.hubname + " WS connection closed - attempt to recontact ISY",
									severity=ConsoleWarning)
				self.lasterror = 'ISYClose'
			elif isinstance(error, websocket.WebSocketTimeoutException):
				logsupport.Logs.Log(self.hubname + " WS connection timed out", severity=ConsoleWarning)
				self.lasterror = 'ISYWSTimeOut'
			elif isinstance(error, TimeoutError):
				logsupport.Logs.Log(self.hubname + " WS socket timed out", severity=ConsoleWarning)
				self.lasterror = 'ISYSocketTimeOut'
			elif isinstance(error, AttributeError):  # Py2 websocket debug todo
				logsupport.Logs.Log(self.hubname + " WS library bug", severity=ConsoleWarning)
				self.lasterror = 'ISYClose'
			elif isinstance(error, OSError):
				if error[0] == errno.ENETUNREACH:
					logsupport.Logs.Log(self.hubname + " WS network down", severity=ConsoleWarning)
					self.lasterror = 'ISYNetDown'
				else:
					logsupport.Logs.Log(self.hubname + ' WS OS error', repr(error), severity=ConsoleError, tb=False)
			else:
				logsupport.Logs.Log(self.hubname + " Error in WS stream " + str(self.QHnum) + ': ' + repr(error),
									severity=ConsoleError,
									tb=True)
				logsupport.Logs.Log(repr(websocket.WebSocketConnectionClosedException))
			self.THstate = 'failed'
			debug.debugPrint('DaemonCtl', "Websocket stream error", self.QHnum, repr(error))
			qws.close()

		# noinspection PyUnusedLocal
		def on_close(qws, code, reason):
			self.isy.HBWS.Entry("Close")
			logsupport.Logs.Log(
				self.hubname + " Websocket stream " + str(self.QHnum) + " closed: " + str(code) + ' : ' + str(reason),
				severity=ConsoleWarning, hb=True)
			debug.debugPrint('DaemonCtl', "ISY Websocket stream closed", str(code), str(reason))

		def on_open(qws):
			self.isy.HBWS.Entry("Open")
			self.THstate = 'starting'
			logsupport.Logs.Log(self.hubname + " Websocket stream " + str(self.QHnum) + " opened")
			debug.debugPrint('DaemonCtl', "Websocket stream opened: ", self.QHnum, self.streamid)
			self.WS = qws

		# noinspection PyUnusedLocal
		def on_message(qws, message):
			self.isy.HBWS.Entry(repr(message))
			try:
				m = 'parse error'
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
						logsupport.Logs.Log(
							self.hubname + " Unexpected event stream change: " + self.streamid + "/" + str(esid),
							severity=ConsoleError, tb=False)
						exitutils.FatalError("WS Stream ID Changed")

					eseq = int(E.pop('@seqnum', -99))
					if self.seq != eseq:
						logsupport.Logs.Log(
							self.hubname + " Event mismatch - Expected: " + str(self.seq) + " Got: " + str(eseq),
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
								logsupport.Logs.Log(self.hubname +
													" State report with no change: " + N.name + ' state: ' + str(
									oldstate))
							else:
								logsupport.Logs.Log(self.hubname +
													" Status change for " + N.name + '(' + str(enode) + ') to ' + str(
									N.devState), severity=ConsoleDetailHigh)
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
										logsupport.Logs.Log(self.hubname + " Node alert fired: " + str(a),
															severity=ConsoleDetail)
										# noinspection PyArgumentList
										PostControl(ISYAlert, hub=self.isy.name, node=enode,
													value=isycodes._NormalizeState(eaction), alert=a)

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
										PostControl(HubNodeChange, hub=self.isy.name, node=enode,
													value=isycodes._NormalizeState(eaction))

					elif (prcode == 'Trigger') and (eaction == '6'):
						vinfo = eInfo['var']
						vartype = int(vinfo['@type'])
						varid = int(vinfo['@id'])
						varval = int(vinfo['val'])
						debug.debugPrint('DaemonCtl', 'Var change: ', valuestore.GetNameFromAttr(self.hubname,(vartype,varid)),' set to ', varval)
						debug.debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid,
								   ' set to ', varval)
						try:
							valuestore.SetValByAttr(self.hubname,(vartype,varid),varval, modifier=True)
						except KeyError:
							logsupport.Logs.Log(
								"Unknown variable from " + self.hubname + " - probably added since startup",
								severity=ConsoleWarning)  # todo cause a restart?

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
						logsupport.Logs.Log(
							self.hubname + " Extra info in event: " + str(ecode) + '/' + str(prcode) + '/' + str(
								eaction) + '/' + str(enode) + '/' + str(eInfo) + str(E), severity=ConsoleWarning)
					debug.debugPrint('DaemonStream', time.time() - config.starttime,
									 formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, E, self.isy))

					try:
						isynd = self.isy.NodesByAddr[enode].name
					except (KeyError, AttributeError):
						isynd = enode
					if ecode == "ERR":
						logsupport.Logs.Log(self.hubname + " shows comm error for node: " + str(isynd),
											severity=ConsoleWarning)
						# logsupport.Logs.Log("-Temp- ", repr(m), repr(message), severity=ConsoleWarning)
						if enode not in self.isy.ErrNodes:
							self.isy.ErrNodes[enode] = self.DoNodeQuery(enode)
					else:
						if enode in self.isy.ErrNodes and (ecode == "ST" or (ecode == "_3" and eaction == "CE")):
							logsupport.Logs.Log(
								self.hubname + " cleared comm error for node: " + str(isynd))
							if enode in self.isy.ErrNodes:
								# logsupport.Logs.Log("Query thread still running")
								del self.isy.ErrNodes[enode]
						#logsupport.Logs.Log("-Temp- ", repr(m), repr(message))

				else:
					logsupport.Logs.Log(self.hubname + " Strange item in event stream: " + str(m),
										severity=ConsoleWarning)
			except Exception as E:
				logsupport.Logs.Log(self.hubname + " Exception in QH on message: ", repr(m), ' Excp: ', repr(E))

		self.THstate = 'delaying'
		logsupport.Logs.Log(self.hubname + " stream thread " + str(self.QHnum) + " setup")
		if self.delayedstart != 0:
			logsupport.Logs.Log(self.hubname + " Delaying Hub restart for probable network reset: ",
								str(self.delayedstart), ' seconds')
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
				logsupport.Logs.Log(self.hubname + " Problem starting WS handler - retrying: ", repr(e))
				print(e)
		self.lastheartbeat = time.time()
		ws.run_forever(ping_timeout=999)
		self.THstate = 'failed'
		self.isy._HubOnline = False
		logsupport.Logs.Log(self.hubname + " QH Thread " + str(self.QHnum) + " exiting", severity=ConsoleWarning,
							tb=False)
