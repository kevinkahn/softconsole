import hubs.hubs
import time
import os
import guicore.guiutils as guiutils
import screens.__screens as screens
from utils.utilfuncs import safeprint
from guicore.screencallmanager import SeqNums, SeqNumLast

import guicore.screenmgt as screenmgt
import guicore.switcher as switcher
from alertsystem import alerttasks
import config
import debug
import logsupport
from utils import timers, threadmanager, exitutils, utilfuncs
from controlevents import CEvent, GetEvent
from logsupport import ConsoleWarning, ConsoleError
from consolestatus import ReportStatus
import controlevents
import traceback

EventDispatch = {}
NewMouse = True

if os.path.exists('/home/pi/.forceoldtouch'): NewMouse = False


def MainControlLoop():
	# Load Event Handlers
	utilfuncs.importmodules('guicore/guievents')

	threadmanager.StartThreads()
	config.sysStore.LogStartTime = time.time()  # MQTT will start tracking other console errors now
	# so we can start broadcasting our errors
	logsupport.LocalOnly = False

	alerttasks.ArmAlerts()

	logsupport.Logs.livelog = False  # turn off logging to the screen
	config.sysStore.ErrorNotice = -1  # don't pester for errors during startup
	time.sleep(1)  # give support services a chance to start (particularly MQTT)
	ReportStatus('mainloop starting')
	config.Running = True

	with open("{}/.ConsoleStart".format(config.sysStore.HomeDir), "a") as f:
		f.write(str(time.time()) + '\n')
	if config.Running:  # allow for a very early restart request from things like autoversion
		switcher.SwitchScreen(screens.HomeScreen, 'Bright', 'Startup', newstate='Home')

	statusperiod = time.time()
	prevstatus = ''

	guiutils.SetUpIntegrity()

	event = None

	pcslist = ''
	for pcs in ('Console', 'Watchdog', 'AsyncLogger', 'Topper'):
		# noinspection PyBroadException
		try:
			if config.sysStore.GetVal(pcs + '_pid') != 0:
				pcslist = pcslist + '{}: {} '.format(pcs, config.sysStore.GetVal(pcs + '_pid'))
		except Exception:
			pass
	logsupport.Logs.Log('Console Up: {}'.format(pcslist))

	stackdepth = 0

	guiutils.SetUpStats()
	lastpgdump = 0

	try:
		while config.Running:  # Operational Control Loop
			guiutils.CycleStats()
			guiutils.HBEvents.Entry('Start event loop iteration')
			if lastpgdump < time.time() - 3600:
				lastpgdump = time.time()
				print('--------------------------', file=open('/home/pi/Console/pgerrors.txt', 'a'))
				for n, s in SeqNums.items():
					print('Thread {}: {}'.format(n, s - SeqNumLast[n]), file=open('/home/pi/Console/pgerrors.txt', 'a'))
					SeqNumLast[n] = s
				print('--------------------------', file=open('/home/pi/Console/pgerrors.txt', 'a'))

			StackCheck = traceback.format_stack()
			if stackdepth == 0:
				stackdepth = len(StackCheck)
			if len(StackCheck) != stackdepth and config.sysStore.versionname in ('development', 'homerelease'):
				logsupport.Logs.Log('Stack growth error', severity=ConsoleWarning, hb=True)
				for L in StackCheck:
					logsupport.Logs.Log(L.strip())

			guiutils.CheckConsoleIntegrity()

			nowtime = time.time()
			if statusperiod <= nowtime or prevstatus != config.sysStore.consolestatus:
				ReportStatus(config.sysStore.consolestatus)
				prevstatus = config.sysStore.consolestatus
				statusperiod = nowtime + 60

			logsupport.LoggerQueue.put(
				(logsupport.Command.Touch, "{}/.ConsoleStart".format(config.sysStore.HomeDir)))

			if debug.dbgStore.GetVal('StatesDump'):
				debug.dbgStore.SetVal('StatesDump', False)
				for h, hub in hubs.hubs.Hubs.items():
					safeprint('States dump for hub: ', h)
					hub.StatesDump()
				debug.dbgStore.SetVal('StatesDump', False)

			if guiutils.Deferrals:  # an event was deferred mid screen touches - handle now
				event = guiutils.Deferrals.pop(0)
				guiutils.HBEvents.Entry('Got deferred event: {}   {}'.format(time.time(), repr(event)))
				debug.debugPrint('EventList', 'Deferred Event Pop', event)
			elif debug.dbgStore.GetVal('QDump'):
				# todo QDump with new event mechanism
				'''if events:
					debug.debugPrint('QDump', 'Time: ', time.time())
					for e in events:
						Deferrals.append(e)
						debug.debugPrint('QDump', e, e.type)
					else:
						debug.debugPrint('QDump', "Empty queue")
						time.sleep(0.01)
				event = pygame.event.Event(NOEVENT, dict={'inject':time.time(),'defer':True}) #eventfix
				'''
				pass
			else:
				needvalidevent = True
				while needvalidevent:
					event = GetEvent()
					guiutils.HBEvents.Entry('Got event: {}  {}'.format(time.time(), repr(event)))
					if event.type == CEvent.ACTIVITYTIMER:
						if event.seq == screenmgt.activityseq:
							needvalidevent = False
						else:
							if utilfuncs.isdevsystem:
								logsupport.Logs.Log(
									'Outdated activity {} {}'.format(event.seq, screenmgt.activityseq))
								guiutils.HBEvents.Entry(
									'outdated activity {} {}'.format(event.seq, screenmgt.activityseq))
								logsupport.DevPrint(
									'outdated activity {} {}'.format(event.seq, screenmgt.activityseq))
					else:
						needvalidevent = False
			guiutils.HBEvents.Entry('Process at {}  {}'.format(time.time(), repr(event)))

			postwaittime = time.time()

			# Dispatch Event
			if event.type in EventDispatch:
				# safeprint('Event: {}'.format(event.type))
				EventDispatch[event.type](event)
			else:
				logsupport.Logs.Log("Unknown main event {}".format(repr(event)), severity=ConsoleError, hb=True,
									tb=False)

			if time.time() - postwaittime > controlevents.latencynotification and not timers.LongOpInProgress:
				# this loop took a long time
				if not config.Exiting:
					logsupport.Logs.Log(
						"Slow loop at {} took {} for {}".format(time.time(), time.time() - postwaittime, event),
						hb=True, homeonly=True)
			guiutils.HBEvents.Entry('End Event Loop took: {}'.format(time.time() - postwaittime))


	except Exception as E:
		logsupport.Logs.Log('Main display loop had exception: {}'.format(repr(E)))
		tbinfo = traceback.format_exc().splitlines()
		for l in tbinfo:
			logsupport.Logs.Log(l)
		config.ecode = exitutils.ERRORRESTART

	logsupport.Logs.Log('Main GUI loop exiting')
