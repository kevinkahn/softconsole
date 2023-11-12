import time

import config
import controlevents
import logsupport
from consolestatus import ReportStatus
from utils import exitutils
from utils.utilfuncs import safeprint
from functools import partial


def ForceRestart(logmsg, exitreason):
	logsupport.Logs.Log(logmsg)
	config.terminationreason = exitreason
	exitutils.Exit(exitutils.AUTORESTART)


def UpdateRestartStatus(logmsg, exitreason):
	ReportStatus('auto restart', hold=2)
	varsnote = config.sysStore.configdir + '/.autovers'
	with open(varsnote, 'w') as f:
		safeprint(time.strftime('%c'), file=f)
	controlevents.PostEvent(
		controlevents.ConsoleEvent(controlevents.CEvent.RunProc, proc=partial(ForceRestart, logmsg, exitreason),
								   name='ForceRestart'))
