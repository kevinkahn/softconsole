import screen
import screens.__screens as screens
import pygame
import debug
import utilities
import hw
import config
import threading, queue
import os
import PIL.Image
import logsupport
from logsupport import ConsoleWarning


class PictureScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname, Clocked=0):
		super().__init__(screensection, screenname, Clocked=1)
		debug.debugPrint('Screen', "Build Picture Screen")

		self.KeyList = None
		utilities.register_example("PictureScreen", self)

		screen.AddUndefaultedParams(self, screensection, picturedir="", picturetime=5)
		if self.picturedir == '':
			self.picturedir = os.path.dirname(config.sysStore.configfile) + '/pics'
		elif self.picturedir[0] != '/':
			self.picturedir = os.path.dirname(config.sysStore.configfile) + '/' + self.picturedir
		self.holdtime = 0
		self.picshowing = None
		self.woffset = 0
		self.hoffset = 0
		self.picture = '*none*'
		self.dirmodtime = 0
		self.picqueue = queue.Queue(maxsize=1)
		self.queueingthread = threading.Thread(name=self.name + 'qthread', target=self.QueuePics, daemon=True)
		self.queueingthread.start()

	# def InitScreen - read the list of pics file to allow updating it
	# keep a line counter for next pic to display (be careful in case list shortens)
	# show next piocture for picture time
	# list file is fn,rotcode  (if no file then just use ls?)

	def QueuePics(self):
		issueerror = True
		blankpic = (pygame.Surface((1, 1)), 1, 1)
		reportedpics = []
		while True:
			dirtime = os.path.getmtime(self.picturedir)
			if dirtime != self.dirmodtime:
				self.dirmodtime = dirtime
				reportedpics = []
				pictureset = os.listdir(self.picturedir)
				for n in pictureset:
					if not n.endswith(('.jpg', '.JPG')): pictureset.remove(n)
				pictureset.sort()
				select = 0
			try:
				picture = pictureset[select]
			except IndexError:
				if len(pictureset) == 0:
					if issueerror:
						logsupport.Logs.Log("Empty picture directory for screen {}".format(self.name),
											severity=ConsoleWarning)
						issueerror = False
					select = -1
				else:
					issueerror = True
					picture = pictureset[0]
					select = 0

			if select == -1:
				picture = '*None*'
				picdescr = blankpic
			else:
				try:
					select += 1
					picdescr = self._preppic(self.picturedir + '/' + picture)
				except Exception as E:
					if picture not in reportedpics:
						logsupport.Logs.Log('Error processing picture {} ({})'.format(picture, E),
											severity=ConsoleWarning)
						reportedpics.append(picture)
					picdescr = blankpic
			self.picqueue.put((picture, picdescr), block=True)

	def InitDisplay(self, nav, specificrepaint=None):
		self.holdtime = 0
		super().InitDisplay(nav)

	def _preppic(self, pic):
		rawp = pygame.image.load(pic)
		try:
			exif = PIL.Image.open(pic)._getexif()[274]
		except Exception:
			exif = 1
		if exif == 6: rawp = pygame.transform.rotate(rawp, 270)  # use 90 for 8. 180 for 3
		ph = rawp.get_height()
		pw = rawp.get_width()
		vertratio = hw.screenheight / ph
		horizratio = hw.screenwidth / pw
		# one of these ratios will yield a scaled picture that is larger that the relevant screen size
		# so pick one and if it is less than the relevant screen dimension use it, otherwise it is the other one
		horizifvertscale = vertratio * pw
		if horizifvertscale < hw.screenwidth:
			scalefac = vertratio
		else:
			scalefac = horizratio
		picframed = pygame.transform.smoothscale(rawp, (int(scalefac * pw), int(scalefac * ph)))
		woffset = (hw.screenwidth - picframed.get_width()) // 2
		hoffset = (hw.screenheight - picframed.get_height()) // 2
		return picframed, woffset, hoffset

	def ScreenContentRepaint(self):
		if not self.Active:
			return  # handle race conditions where repaint queued just before screen switch

		self.holdtime -= 1
		if self.holdtime <= 0:
			# get new picture
			try:
				self.picture, picdescr = self.picqueue.get_nowait()
				self.holdtime = self.picturetime
				self.picshowing, self.woffset, self.hoffset = picdescr

			except queue.Empty:
				logsupport.Logs.Log('Picture not ready for screen {} holding {}'.format(self.name, self.picture),
									severity=ConsoleWarning)
		hw.screen.blit(self.picshowing, (self.woffset, self.hoffset))


screens.screentypes["Picture"] = PictureScreenDesc
