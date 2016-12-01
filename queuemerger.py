import config
from logsupport import ConsoleWarning, ConsoleError
from debug import debugPrint
import pygame, time


def Qhandler():
	# integrate the daemon reports into the pygame event stream
	while True:
		debugPrint('DaemonCtl', "Q size at main loop ", config.fromDaemon.qsize())
		item = config.fromDaemon.get()
		if item[0] == "Log":
			config.Logs.Log(item[1], severity=item[2])
		elif item[0] == "Node":
			if item[1] in config.DS.WatchNodes:
				debugPrint('DaemonCtl', 'ISY reports change(alert):', str(item))
				for a in config.DS.WatchNodes[item[1]]:
					config.Logs.Log("Node alert fired: " + str(a))
					notice = pygame.event.Event(config.DS.ISYAlert, node=item[1], value=item[2], alert=a)
					pygame.fastevent.post(notice)
			if item[1] in config.DS.AS.NodeWatch:
				debugPrint('DaemonCtl', time.time(), "ISY reports change: ", "Key: ", str(item))
				notice = pygame.event.Event(config.DS.ISYChange, node=item[1], value=item[2])
				pygame.fastevent.post(notice)
		elif item[0] == "VarChg":
			config.DS.WatchVarVals[(item[1], item[2])] = item[3]
			if item[1] == 1:
				debugPrint('DaemonCtl', 'Int var change: ', config.ISY.varsIntInv[item[2]], ' <- ', item[3])
			elif item[1] == 2:
				debugPrint('DaemonCtl', 'State var change: ', config.ISY.varsStateInv[item[2]], ' <- ', item[3])
			else:
				config.Logs.Log('Bad var message from daemon' + str(item[1]), severity=ConsoleError)

			for a in config.DS.WatchVars[(item[1], item[2])]:
				config.Logs.Log("Var alert fired: " + str(a))
				notice = pygame.event.Event(config.DS.ISYVar, vartype=item[1], varid=item[2], value=item[3], alert=a)
				pygame.fastevent.post(notice)
		else:
			config.Logs.Log("Bad msg from watcher: " + str(item), Severity=ConsoleWarning)
