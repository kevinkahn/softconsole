import config
import utilities


def InBut(pos, Key):
	return (pos[0] > Key.Center[0] - Key.Size[0]/2) and (pos[0] < Key.Center[0] + Key.Size[0]/2) and \
		   (pos[1] > Key.Center[1] - Key.Size[1]/2) and (pos[1] < Key.Center[1] + Key.Size[1]/2)


class TouchPoint(object):
	"""
	Represents a touchable rectangle on the screen.
	"""

	def __init__(self, c, s):
		self.Center = c
		self.Size = s
		utilities.register_example("TouchPoint", self)


class ManualKeyDesc(TouchPoint):
	"""
	Defines a drawn touchable rectangle on the screen that represents a key (button).  May be called with one of 2
	signatures.  It can be called manually by code to create a key by supplying all the attributes of the key in the
	code explicitly.  It can also be called with a config objects section in which case it will build the key from the
	combination of the defaults for the attributes and the explicit overides found in the config.txt file section
	that is passed in.
	"""

	def __init__(self, *args, **kwargs):
		# alternate creation signatures
		if len(args) == 2:
			# signature: ManualKeyDesc(keysection, keyname)
			# initialize by reading config file
			self.dosectioninit(*args)
		else:
			# signature: ManualKeyDesc(keyname, label, bcolor, charcoloron, charcoloroff, center=, size=, KOn=, KOff=, proc=)
			# initializing from program code case
			self.docodeinit(*args, **kwargs)
		utilities.register_example("ManualKeyDesc", self)

	def docodeinit(self, keyname, label, bcolor, charcoloron, charcoloroff, center=(0, 0), size=(0, 0), KOn='', KOff='',
				   proc=None):
		# NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
		# because of when config is imported and what walues are at that time versus at call time
		TouchPoint.__init__(self, center, size)
		self.name = keyname
		self.RealObj = proc
		self.KeyColor = bcolor
		self.KeyCharColorOn = charcoloron
		self.KeyCharColorOff = charcoloroff
		self.State = True
		self.label = label
		self.KeyOnOutlineColor = config.KeyOnOutlineColor if KOn == '' else KOn
		self.KeyOffOutlineColor = config.KeyOffOutlineColor if KOff == '' else KOff

	def dosectioninit(self, keysection, keyname):
		TouchPoint.__init__(self, (0, 0), (0, 0))
		utilities.LocalizeParams(self, keysection, 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
								 'KeyCharColorOn', 'KeyCharColorOff', label=[keyname])
		self.name = keyname
		self.State = True
		self.RealObj = None  # this will get filled in by creator later - could be ISY node, ISY program, proc to call

	def FinishKey(self,center,size):
		pass
		#if center/size not 0 then set them
		#create a surface that is the key "on" and one that is the key "off"
		#need to deal with late bound labels like conditions/forecast
		#need a paint key that blits to surface
