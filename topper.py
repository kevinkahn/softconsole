import os
import historybuffer
import shutil
import multiprocessing
import time
import signal


topdir = ''
topseq = 0


def inittop():
	global topdir
	topdir = historybuffer.HBdir+'Tops'
	os.mkdir(topdir)
	os.mkdir(topdir+'/Current')
	TopP = multiprocessing.Process(target=dotops)
	TopP.daemon = True
	TopP.start()

def dotops():
	global topseq
	signal.signal(signal.SIGTERM, signal.SIG_DFL)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	while True:
		try:
			os.system('top -bn1 > '+topdir+'/Current/{:08d}'.format(topseq))
			if topseq - 30 >= 0:
				try:
					os.remove(topdir+'/Current/{:08d}'.format(topseq-30))
				except:
					pass
			topseq +=1
		except Exception as E:
			print('topper exception: {}'.format(E))
		time.sleep(1)


def mvtops(dirnm):
	global topseq
	try:
		shutil.move(topdir+'/Current/',topdir+'/'+dirnm)
		os.mkdir(topdir + '/Current')
	except Exception as E:
		print('mvtops exception: {}'.format(E))
