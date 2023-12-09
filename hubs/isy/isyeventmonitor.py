import base64
import errno
import random
import ssl
import threading
import time
import copy

import websocket
import xmltodict

import config
import debug
from utils import exitutils
import hubs.isy.isycodes as isycodes
import logsupport
from controlevents import CEvent, PostEvent, ConsoleEvent, PostIfInterested
from hubs.isy.isycodes import EVENT_CTRL, formatwsitem
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail, ConsoleDetailHigh
from utils.threadmanager import ThreadStartException
from utils.utilfuncs import safeprint


class ISYEMInternalError(Exception):
	pass


def BaseAddr(addr):
	return None if addr is None else ' '.join(addr.split(' ')[0:-1])


class ISYEventMonitor(object):

	def __init__(self, thisISY):
		self.connectionmode = 'try994'
		# trypolisy: trying without subp, polisy: connection worked, try994: trying with subp 994worked.
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
		self.longdown = 0
		self.WS = None
		self.THstate = 'init'
		self.querycnt = 0
		self.queryqueued = {}
		self.LastMsgErr = ('***', -99)
		self.isy.Busy = 0

		self.lasterror = 'Init'
		debug.debugPrint('DaemonCtl', "Queue Handler ", self.QHnum, " started: ", self.watchstarttime)
		self.reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "CLISP", "CLISPH", "CLISPC", "CLIFS",
								"CLIMD", "CLIHUM", "CLIHCS", "BRT", "DIM"]  # "RR", "OL",

	def EndWSServer(self):
		self.lasterror = "DirectCommError"
		self.WS.close()

	def RealQuery(self, enode, seq, ndnm):
		logsupport.Logs.Log("Queued query attempt (" + str(seq) + ") for: " + ndnm)
		time.sleep(105 + random.randint(0, 30))  # allow any in progress query at ISY a chance to clear
		if enode not in self.isy.ErrNodes:
			logsupport.Logs.Log("Node error cleared without need of query (" + str(seq) + ") for: " + ndnm)
			return
		logsupport.Logs.Log(self.hubname + ": Attempt query (" + str(seq) + ") for errored node: " + ndnm,
							severity=ConsoleWarning)
		r = self.isy.try_ISY_comm('query/' + enode, timeout=60, closeonfail=False)
		if r == '':
			logsupport.Logs.Log(self.hubname + ": Query (" + str(seq) + ") attempt failed for node: " + ndnm,
								severity=ConsoleWarning)
		else:
			time.sleep(2)
			logsupport.Logs.Log(self.hubname + ": Query (" + str(seq) + ") attempt succeeded for node: " + ndnm)
		if enode in self.isy.ErrNodes:
			del self.isy.ErrNodes[enode]
		if enode in self.queryqueued:
			del self.queryqueued[enode]

	def DoNodeQuery(self, enode, ndnm):
		if enode not in self.queryqueued:
			self.querycnt += 1
			self.queryqueued[enode] = self.querycnt
			t = threading.Thread(name='Query-' + str(self.querycnt) + '-' + enode, target=self.RealQuery, daemon=True,
								 args=(enode, self.querycnt, ndnm))
			t.start()
		else:
			logsupport.Logs.Log(
				self.hubname + ": Query " + str(self.queryqueued[enode]) + " already queued for node: " + ndnm)

	def FakeNodeChange(self):
		# noinspection PyArgumentList
		PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.isy.name, node=None, value=-1))

	def reinit(self):
		self.watchstarttime = time.time()
		self.watchlist = []
		self.seq = 0
		self.hbcount = 0
		self.QHnum += 1

	def PostStartQHThread(self):
		if self.isy.version == -1:
			# test mode
			return
		hungcount = 40
		while self.THstate == 'restarting':
			logsupport.Logs.Log(self.hubname + " Waiting thread start")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0:
				raise ThreadStartException
		while self.THstate == 'delaying':
			time.sleep(1)
		hungcount = 60
		while self.THstate == 'starting':
			logsupport.Logs.Log(self.hubname + ": Waiting initial status dump")
			time.sleep(2)
			hungcount -= 1
			if hungcount < 0:
				raise ThreadStartException
		if self.THstate == 'running':
			self.isy._HubOnline = True
			self.isy.Vars.CheckValsUpToDate(reload=True)
			logsupport.Logs.Log(self.hubname + ": Initial status streamed ", self.seq, " items and vars updated")
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
				self.delayedstart = 121
			elif self.lasterror == 'ISYClose':
				logsupport.Logs.Log(self.hubname + ' Recovering closed WS stream')
				self.delayedstart = 2
			elif self.lasterror == 'DirectCommError':
				logsupport.Logs.Log(self.hubname + ' WS restart because of failed direct communication failure')
				self.delayedstart = 90  # probably ISY doing query
			elif self.lasterror == 'ISYNoRoute':
				logsupport.Logs.Log("{}: Hub probably down (semi) permanently ({})".format(self.hubname, self.longdown))
				self.delayedstart = 3600 + self.longdown * 1800  # spread checks way out
				self.isy._HubOnline = False
				self.longdown += 1
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
			reconsev = ConsoleWarning if config.sysStore.ErrLogReconnects else logsupport.ConsoleInfo
			if isinstance(error, websocket.WebSocketConnectionClosedException):
				logsupport.Logs.Log(self.hubname + " WS connection closed - attempt to recontact ISY",
									severity=reconsev)
				self.lasterror = 'ISYClose'
			elif isinstance(error, websocket.WebSocketTimeoutException):
				logsupport.Logs.Log(self.hubname + " WS connection timed out", severity=ConsoleWarning)
				self.lasterror = 'ISYWSTimeOut'
			elif isinstance(error, TimeoutError):
				logsupport.Logs.Log(self.hubname + " WS socket timed out", severity=ConsoleWarning)
				self.lasterror = 'ISYSocketTimeOut'
			elif isinstance(error, AttributeError):
				logsupport.Logs.Log(self.hubname + " WS library bug", severity=ConsoleWarning)
				self.lasterror = 'ISYClose'
			elif isinstance(error, OSError):
				if error.errno == errno.ENETUNREACH:
					logsupport.Logs.Log(self.hubname + " WS network down", severity=ConsoleWarning)
					self.lasterror = 'ISYNetDown'
				else:
					logsupport.Logs.Log(self.hubname + ' WS OS error', repr(error), severity=ConsoleError, tb=False)
					self.lasterror = 'ISYNoRoute'  # probably semi permanent failure
			else:
				if self.connectionmode == 'try994':
					logsupport.Logs.Log("{}: Connection failed using 994 convention".format(self.hubname))
					self.connectionmode = 'trypolisy'
				elif self.connectionmode == 'trypolisy':
					logsupport.Logs.Log("{}: Connection failed using Polisy convention".format(self.hubname))
					self.connectionmode = 'try994'
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
			reconsev = ConsoleWarning if config.sysStore.ErrLogReconnects else logsupport.ConsoleInfo
			logsupport.Logs.Log("{} WS stream {} closed: {}:{}".format(self.hubname, self.QHnum, code, reason),
								severity=reconsev, hb=True)
			debug.debugPrint('DaemonCtl', "ISY Websocket stream closed", str(code), str(reason))

		def on_open(qws):
			self.isy.HBWS.Entry("Open")
			self.THstate = 'starting'
			if self.connectionmode == 'try994':
				self.connectionmode = '994worked'
				logsupport.Logs.Log('{} connection worked using 994 convention'.format(self.isy.name))
			elif self.connectionmode == 'trypolisy':
				self.connectionmode = 'polisyworked'
				logsupport.Logs.Log('{} connection worked using Polisy convention'.format(self.isy.name))
			mess = '994' if (self.connectionmode
							 == '994worked') else 'Polisy' if self.connectionmode == 'polisyworked' else self.connectionmode
			logsupport.Logs.Log("{}: WS stream {} opened ({})".format(self.hubname, self.QHnum, mess))
			debug.debugPrint('DaemonCtl', "Websocket stream opened: ", self.QHnum, self.streamid)
			self.WS = qws

		# noinspection PyUnusedLocal,PyUnboundLocalVariable
		def on_message(qws, message):

			loopstart = time.time()
			self.isy.HBWS.Entry('Message: {}'.format(repr(message)))

			# print('Message: {}'.format(message))
			try:
				m = 'parse error'
				m = xmltodict.parse(message)
				msav = copy.deepcopy(m)
				if debug.dbgStore.GetVal('ISYDump'):
					debug.ISYDump("isystream.dmp", message, pretty=False)

				# print(m)

				if 'SubscriptionResponse' in m:
					sr = m['SubscriptionResponse']
					if self.streamid != sr['SID']:
						self.streamid = sr['SID']
						logsupport.Logs.Log("{}: Stream id: {}".format(self.hubname, self.streamid))

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
						eaction = eaction["#text"]  # the new xmltodict will return as data['action']['#text']

					if enode in self.isy.NodesByAddr:  # get the node to set if any
						N = self.isy.NodesByAddr[enode]
					else:
						N = None

					if ecode == 'ST':  # update cached state first before posting alerts or race

						if isinstance(N, isycodes.ThermType):
							N.cur = isycodes.NormalizeState(eaction)
						elif N is not None:
							oldstate = N.devState
							N.devState = isycodes.NormalizeState(eaction)
							logsupport.Logs.Log('ISYchg', 'ISY Node: ', N.name, ' state change from: ', oldstate,
												' to: ', N.devState, severity=ConsoleDetailHigh)
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
												a.state = 'Init'
										logsupport.Logs.Log(self.hubname + " Node alert fired: " + str(a),
															severity=ConsoleDetail)
										# noinspection PyArgumentList
										PostEvent(ConsoleEvent(CEvent.ISYAlert, hub=self.isy.name, node=enode,
															   value=isycodes.NormalizeState(eaction), alert=a))
					elif ecode == 'CLIHCS' and isinstance(N, isycodes.ThermType):
						N.statecode = isycodes.NormalizeState(eaction)
					elif ecode == 'CLIFS' and isinstance(N, isycodes.ThermType):
						N.fancode = isycodes.NormalizeState(eaction)
					elif ecode == 'CLIMD' and isinstance(N, isycodes.ThermType):
						N.modecode = isycodes.NormalizeState(eaction)
					elif ecode == 'CLIHUM' and isinstance(N, isycodes.ThermType):
						N.hum = isycodes.NormalizeState(eaction)
					elif ecode == 'CLISPH' and isinstance(N, isycodes.ThermType):
						N.setlow = isycodes.NormalizeState(eaction)
					elif ecode == 'CLISPC' and isinstance(N, isycodes.ThermType):
						N.sethigh = isycodes.NormalizeState(eaction)

					if ecode in self.reportablecodes:
						# Node change report
						debug.debugPrint('DaemonStream', time.time() - config.sysStore.ConsoleStartTime,
										 "Status update in stream: ",
										 eseq, ":",
										 prcode, " : ", enode, " : ", eInfo, " : ", eaction)

						# logsupport.Logs.Log('reportable event '+str(ecode)+' for '+str(enode)+' action '+str(eaction))

						PostIfInterested(self.isy, enode, isycodes.NormalizeState(eaction))

					elif (prcode == 'Trigger') and (eaction == '6'):
						vinfo = eInfo['var']
						vartype = int(vinfo['@type'])
						varid = int(vinfo['@id'])
						varval = int(vinfo['val'])
						debug.debugPrint('DaemonCtl', 'Var change: ', self.isy.Vars.GetNameFromAttr((vartype, varid)),
										 ' set to ', varval)
						debug.debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype],
										 ' variable ', varid,
										 ' set to ', varval)
						try:
							self.isy.Vars.SetValByAttr((vartype, varid), varval, modifier=True)
						except KeyError:
							logsupport.Logs.Log(
								"Unknown variable from " + self.hubname + " - probably added since startup",
								severity=ConsoleWarning)

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
					efmtnm = E.pop('fmtName', 'noName')
					if E:
						lev = ConsoleDetailHigh if str(
							enode) in self.isy.V3Nodes else ConsoleWarning  # supress to detail if it is a V3 node
						logsupport.Logs.Log(
							self.hubname + " Extra info in event: " + str(ecode) + '/' + str(prcode) + '/' + str(
								eaction) + '/' + str(enode) + '/' + str(eInfo) + '   ' + str(E), severity=lev)
					debug.debugPrint('DaemonStream', time.time() - config.sysStore.ConsoleStartTime,
									 formatwsitem(esid, eseq, ecode, eaction, enode, eInfo, E, self.isy))

					try:
						isynd = self.isy.NodesByAddr[enode].name
					except (KeyError, AttributeError):
						isynd = enode

					if ecode == '_5':
						now = time.time()
						if str(eaction) == '1':
							# logsupport.Logs.Log(self.hubname, ' went busy')
							self.isy.Busy = now
						elif str(eaction) == '0':
							if self.isy.Busy != 0:
								# logsupport.Logs.Log(self.hubname, " cleared busy")
								if now - self.isy.Busy > 10:
									logsupport.Logs.Log(
										"{}: busy for {:.4f} seconds".format(self.hubname, now - self.isy.Busy))
								self.isy.Busy = 0
							else:
								logsupport.Logs.Log(self.hubname, " reported stand-alone not busy")
						else:
							logsupport.Logs.Log(self.hubname, " reported System Status: ", str(eaction))

					if ecode == "ST" or (ecode == "_3" and eaction == "CE"):
						if self.LastMsgErr[0] != '***' and (
								BaseAddr(self.LastMsgErr[0]) == BaseAddr(enode)):
							# ERR msg followed by clearing - ISY weirdness?
							logsupport.Logs.Log(
								"{} reported and immediately cleared error for node: {} ({}) (seq:{}/{})".format(
									self.hubname,
									isynd, BaseAddr(self.LastMsgErr[0]), self.LastMsgErr[1], eseq),
								severity=ConsoleWarning, hb=True)
							self.LastMsgErr = ('***', -99)
						elif enode in self.isy.ErrNodes:
							logsupport.Logs.Log("{} cleared comm error for node: {}".format(self.hubname, isynd))
							if enode in self.isy.ErrNodes:
								# logsupport.Logs.Log("Query thread still running")
								del self.isy.ErrNodes[enode]

					if self.LastMsgErr != ('***', -99):
						# previous message was ERR and wasn't immediately cleared
						try:
							isyerrnd = self.isy.NodesByAddr[self.LastMsgErr[0]].name
						except (KeyError, AttributeError):
							isyerrnd = self.LastMsgErr[0]
						logsupport.Logs.Log(
							"{} WS stream shows comm error for node: {}(Seq:{})".format(self.hubname, isyerrnd,
																						self.LastMsgErr[1]),
							severity=ConsoleWarning, hb=True)
						if self.LastMsgErr[0] not in self.isy.ErrNodes:
							self.isy.ErrNodes[self.LastMsgErr[0]] = eseq
							self.DoNodeQuery(self.LastMsgErr[0], isyerrnd)
						self.LastMsgErr = ('***', -99)

					if ecode == "ERR":
						if str(eaction) == "0":
							pass
						# logsupport.Logs.Log("ERR(0) seen: {}".format(repr(m)))
						else:
							# Note the error and wait one message to see if it immediately clears
							self.LastMsgErr = (enode, eseq)
							logsupport.Logs.Log("ERR(1) seen: {}".format(repr(xmltodict.parse(message))),
												severity=ConsoleWarning)

					if ecode == "_3" and eaction == "NE":
						self.LastMsgErr = (enode, eseq)
						logsupport.Logs.Log(
							"{} WS stream reported NE error code on WS stream for node{}(Seq:{})".format(self.hubname,
																										 isynd, eseq),
							hb=True)

				else:
					logsupport.Logs.Log(self.hubname + " Strange item in event stream: " + str(m),
										severity=ConsoleWarning)
					safeprint(message)
			except Exception as E:
				logsupport.Logs.Log(self.hubname + " Exception in QH on message: ", repr(msav), ' Excp: ', repr(E),
									severity=ConsoleWarning)
			loopend = time.time()
			self.isy.HBWS.Entry('Processing time: {} Done: {}'.format(loopend - loopstart, repr(
				message)))
			time.sleep(.001)  # force thread to give up processor to allow response to time events

		if self.isy.version == -1:
			self.isy._HubOnline = True
			time.sleep(7)
			with open('/home/pi/Console/isystream.dmp', 'r') as f:
				f.readline()  # absorb first
				# safeprint("Message1: {}".format(mes))
				while True:
					mes = f.readline().rstrip('\n')
					if mes == '':
						# safeprint('Done')
						break
					# safeprint("Message: {}".format(mes))
					on_message(None, mes)
				time.sleep(.4)
			while True:
				time.sleep(500)
			# noinspection PyUnreachableCode
			return
		self.THstate = 'delaying'
		logsupport.Logs.Log("{}: WS stream thread {} setup".format(self.hubname, self.QHnum), severity=ConsoleDetail)
		if self.delayedstart != 0:
			logsupport.Logs.Log(self.hubname + " Delaying Hub restart for probable network reset: ",
								str(self.delayedstart), ' seconds')
			time.sleep(self.delayedstart)
		# websocket.enableTrace(True)
		websocket.setdefaulttimeout(30)
		if self.isy.addr.startswith('http://'):
			wsurl = 'ws://' + self.isy.addr[7:] + '/rest/subscribe'
		elif self.isy.addr.startswith('https://'):
			wsurl = 'wss://' + self.isy.addr[8:] + '/rest/subscribe'
		else:
			wsurl = 'ws://' + self.isy.addr + '/rest/subscribe'
		import logging
		WStrace = open('/home/pi/WStrace', 'w')
		print('Open {}'.format(wsurl), file=WStrace)
		websocket.enableTrace(True, handler=logging.StreamHandler(stream=WStrace))
		while True:
			try:
				# noinspection PyArgumentList
				if self.connectionmode in ('trypolisy', 'polisyworked'):
					ws = websocket.WebSocketApp(wsurl, on_message=on_message,
												on_error=on_error,
												on_close=on_close, on_open=on_open,
												header={'Authorization': 'Basic ' + self.a.decode('ascii')})
				else:
					ws = websocket.WebSocketApp(wsurl, on_message=on_message,
												on_error=on_error,
												subprotocols=['ISYSUB'],
												on_close=on_close, on_open=on_open,
												header={'Authorization': 'Basic ' + self.a.decode('ascii')})
				break
			except AttributeError as e:
				logsupport.Logs.Log(self.hubname + " Problem starting WS handler - retrying: ", repr(e))
		self.lastheartbeat = time.time()
		ws.run_forever(ping_timeout=999, sslopt={"cert_reqs": ssl.CERT_NONE})
		self.THstate = 'failed'
		self.isy._HubOnline = False
		sev = ConsoleWarning if config.sysStore.ErrLogReconnects else logsupport.ConsoleInfo
		logsupport.Logs.Log(self.hubname + " QH Thread " + str(self.QHnum) + " exiting", severity=sev,
							tb=False)
