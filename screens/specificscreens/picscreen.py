ScreenType = 'Picture'
from screens import screen
import screens.__screens as screens
from guicore.screencallmanager import pg
import debug
from utils import utilities, threadmanager, hw
import time
import config
from threading import Event
from queue import Queue, Empty
import os
import subprocess
import shutil
import PIL.Image
import PIL.ExifTags
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail


class PictureScreenDesc(screen.ScreenDesc):
	def _reset_cache(self):
		self.piccache = {}
		self.cachedir = config.sysStore.configdir + '/.pics-{}/'.format(self.name)
		shutil.rmtree(self.cachedir, ignore_errors=True)
		os.mkdir(self.cachedir)

	def __init__(self, screensection, screenname):
		super().__init__(screensection, screenname, Type=ScreenType)
		debug.debugPrint('Screen', "Build Picture Screen")

		self.KeyList = None
		self.shownav = False
		utilities.register_example("PictureScreen", self)
		self.piccache = {}
		self.missingpicdir = False
		# self._reset_cache() not needed because initial modtime value forces it on first pass

		screen.AddUndefaultedParams(self, screensection, picturedir="", picturetime=5, singlepic='', NavKeyAlpha=-1)
		self.singlepicmode = self.singlepic != ''
		if self.singlepicmode:
			self.singlepic = utilities.inputfileparam(self.singlepic, config.sysStore.configdir, '/pic.jpg')
			logsupport.Logs.Log('Picture screen {} in single mode for {}'.format(self.name, self.singlepic))
			self.picturetime = 9999
		else:
			self.picturedir = utilities.inputfileparam(self.picturedir, config.sysStore.configdir, '/pics')
			if '*' in self.picturedir: self.picturedir = self.picturedir.replace('*', config.sysStore.hostname)
			logsupport.Logs.Log('Picture screen {} in directory mode for {}'.format(self.name, self.picturedir))
			if not os.path.exists(self.picturedir):
				logsupport.Logs.Log(
					"Can't find picture directory {}; try mount".format(self.picturedir, severity=ConsoleWarning))
				mntres = subprocess.run(['mount', '-a'])
				logsupport.Logs.Log("Mount result: {}".format(mntres))
				if not os.path.exists(self.picturedir):
					logsupport.Logs.Log("Still no picture directory - defer screen start", severity=ConsoleWarning)
					self.missingpicdir = True

		if self.NavKeyAlpha == -1: self.NavKeyAlpha = None
		self.holdtime = 0
		self.blankpic = (pg.Surface((1, 1)), 1, 1)
		self.picshowing = self.blankpic[0]
		self.woffset = 1
		self.hoffset = 1
		self.picture = '*none*'
		self.modtime = 0
		self.picqueue = Queue(maxsize=1)
		self.DoSinglePic = Event()
		self.DoSinglePic.set()
		if self.missingpicdir:
			threadmanager.SetUpHelperThread(self.name + '-deferpicdir', self.RetryDirMount, prestart=None,
											poststart=None, prerestart=None, postrestart=None, checkok=None)
		else:
			threadmanager.SetUpHelperThread(self.name + '-picqueue',
											[self.QueuePics, self.QueueSinglePic][self.singlepicmode], prestart=None,
											poststart=None, prerestart=None, postrestart=None, checkok=None)

	def RetryDirMount(self):
		defertime = 300
		while self.missingpicdir:
			logsupport.Logs.Log(f"Will retry picture directory mount for {self.name} in {defertime} seconds")
			time.sleep(defertime)
			logsupport.Logs.Log(f'Try mount for picture directory {self.picturedir}')
			mntres = subprocess.run(['mount', '-a'])
			logsupport.Logs.Log("Mount result: {}".format(mntres))
			if not os.path.exists(self.picturedir):
				logsupport.Logs.Log("Still no picture directory - defer screen", severity=ConsoleWarning)
			else:
				logsupport.Logs.Log(f'Got picture directory {self.picturedir} for {self.name}')
				self.missingpicdir = False
				threadmanager.SetUpHelperThread(self.name + '-picqueue',
												[self.QueuePics, self.QueueSinglePic][
													self.singlepicmode], prestart=None,
												poststart=None, prerestart=None, postrestart=None,
												checkok=None)
		logsupport.Logs.Log(f'Exiting deferal thread for {self.name}')


	def QueueSinglePic(self):
		while True:
			pictime = os.path.getmtime(self.singlepic)
			if pictime != self.modtime:
				self.modtime = pictime
				picdescr = self._preppic(self.singlepic)
				self.picqueue.put(('*single*', picdescr), block=True)
				self.holdtime = -1
			time.sleep(1)

	def QueuePics(self):
		issueerror = True
		reportedpics = []
		pictureset = []
		select = 0
		emptypicdir = False
		try:
			while True:
				dirtime = os.path.getmtime(self.picturedir)
				if (dirtime != self.modtime) or emptypicdir:  # second option is to handle net disconnect
					self.modtime = dirtime
					reportedpics = []
					self._reset_cache()
					pictureset = os.listdir(self.picturedir)
					emptypicdir = False  # assume it ok now
					picsettrimmed = pictureset.copy()
					for n in pictureset:
						if not n.endswith(('.jpg', '.JPG')):
							picsettrimmed.remove(n)
					pictureset = picsettrimmed
					pictureset.sort()
					logsupport.Logs.Log('Screen {} reset using {} pictures'.format(self.name, len(pictureset)))
					select = 0
				try:
					picture = pictureset[select]
				except IndexError:
					if len(pictureset) == 0:
						picture = '*Empty*'
						emptypicdir = True
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
					picdescr = self.blankpic
				else:
					pictime = os.path.getmtime(self.picturedir + '/' + picture)
					savpic = picture.rpartition('.')[0] + ".bmp"
					if picture in self.piccache and pictime == self.piccache[picture][0]:
						select += 1
						try:
							picdescr = (
								pg.image.load(self.cachedir + savpic), self.piccache[picture][1],
								self.piccache[picture][2])
						except Exception as E:
							logsupport.Logs.Log(
								'{} screen cache consistency error for {} ({})'.format(self.name, picture, E),
								severity=ConsoleWarning)
							picdescr = self.blankpic
							self._reset_cache()
					else:
						try:
							select += 1
							picdescr = self._preppic(self.picturedir + '/' + picture)
						except Exception as E:
							if picture not in reportedpics:
								logsupport.Logs.Log('Error processing picture {} ({})'.format(picture, E),
													severity=ConsoleWarning)
								reportedpics.append(picture)
							picdescr = self.blankpic
						self.piccache[picture] = (pictime, picdescr[1], picdescr[2])
						pg.image.save(picdescr[0], self.cachedir + savpic)
				self.picqueue.put((picture, picdescr), block=True)
		except Exception as E:
			logsupport.Logs.Log('{} picture handling thread exception: {}'.format(self.name, E),
								severity=ConsoleWarning)

	def InitDisplay(self, nav):
		if not nav is None:
			self.shownav = True
			for n, k in nav.items(): k.SetOnAlpha(self.NavKeyAlpha)
		if not self.singlepicmode: self.holdtime = 0
		super().InitDisplay(nav)

	@staticmethod
	def _preppic(pic):
		rawp = pg.image.load(pic)
		# noinspection PyBroadException
		try:
			exinfo = PIL.Image.open(pic).getexif()
			exif = exinfo[PIL.ExifTags.Base.Orientation.value]
		except:
			exif = 1
		#		print("{} rot: {}".format(pic,exif))
		rot = [0, 0, 0, 180, 0, 0, 270, 0, 90][exif]
		if rot != 0: rawp = pg.transform.rotate(rawp, rot)
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
		picframed = pg.transform.smoothscale(rawp, (int(scalefac * pw), int(scalefac * ph)))
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

			except Empty:
				if not self.singlepicmode:  # normal case in single mode is nothing changed
					logsupport.Logs.Log('Picture not ready for screen {} holding {} ({})'.format(self.name,
																								 self.picture,
																								 self.holdtime),
										severity=ConsoleDetail)
		hw.screen.blit(self.picshowing, (self.woffset, self.hoffset))
		if self.shownav: self.PaintNavKeys()


screens.screentypes[ScreenType] = PictureScreenDesc
