# junk module at this time
print("Pygame thread module imported -- junk!")

import pygame
import pygame.gfxdraw
import logsupport
from logsupport import ConsoleWarning
from guicore.screencallmanager import ToPygame, FromPygame, SeqNums, initq, rem, remobj
import threading


def DoPygameOps():
	try:
		while True:
			callparms = ToPygame.get()

			# callhist.append('Exec: {}'.format(callparms))
			if callparms[1] == rem:
				op = callparms[2].split('.')
				fn = pygame
				for i in op:
					fn = fn.__dict__[i]
				res = fn(*callparms[3], **callparms[4])
			elif callparms[1] == remobj:
				obj = callparms[2]
				func = callparms[3]
				res = obj.__class__.__dict__[func](obj, *callparms[4], **callparms[5])
			elif callparms[1] == initq:
				SeqNums[callparms[0][0]] = 0
				FromPygame[callparms[0][0]] = queue.SimpleQueue()
				res = 'ok'
			else:  # report error
				logsupport.Logs.Log('Pygame sequence error {}:{} <> {}'.format(callparms[0][0], callparms[0][1],
																			   callparms[2]), severity=ConsoleWarning)
				for i in callparms[3]:
					logsupport.Logs.Log('{}'.format(i))
				res = 'ok'

			FromPygame[callparms[0][0]].put((callparms[0], res))
	except Exception as E:
		print('Pygame Thread excetion {}'.format(E))


PyGameExec = None


def StartPyGameDaemon():
	print('Thread module')
	PyGameExec = threading.Thread(target=DoPygameOps)
	PyGameExec.start()
