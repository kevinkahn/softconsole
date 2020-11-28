import os
import historybuffer
import shutil
import multiprocessing
import time
import signal
import logsupport
import config


topdir = ''
topseq = 0
TopP = None


def inittop():
	global topdir, TopP
	topdir = historybuffer.HBdir + 'Tops'
	os.mkdir(topdir)
	os.mkdir(topdir + '/Current')
	TopP = multiprocessing.Process(target=dotops, name='Topper')
	TopP.daemon = True
	TopP.start()
	# os.system('echo WLAN > /home/pi/Console/wlan')
	config.sysStore.SetVal('Topper_pid', TopP.pid)
	logsupport.Logs.Log('Started top check process: {}'.format(TopP.pid))


# noinspection PyUnusedLocal
def IgnoreHUP(signum, frame):
	logsupport.DevPrint('Topper got HUP - ignoring')


def dotops():
	global topseq
	signal.signal(signal.SIGTERM, signal.SIG_DFL)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	signal.signal(signal.SIGHUP, IgnoreHUP)
	while True:
		try:
			#os.system('date >> /home/pi/Console/wlan')
			#os.system('iwconfig wlan0 >> /home/pi/Console/wlan')
			os.system('top -bn1 > '+topdir+'/Current/{:08d}'.format(topseq))
			if topseq - 30 >= 0:
				# noinspection PyBroadException
				try:
					os.remove(topdir + '/Current/{:08d}'.format(topseq - 30))
				except:
					pass
			topseq +=1
		except Exception as E:
			print('topper exception: {}'.format(E))
		time.sleep(1)


def mvtops(dirnm):
	global topseq, TopP
	if TopP is not None:
		try:
			shutil.move(topdir + '/Current/', topdir + '/' + dirnm)
			os.mkdir(topdir + '/Current')
		except Exception as E:
			print('mvtops exception: {}'.format(E))
