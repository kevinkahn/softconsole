class KeyDesc(object):  # todo delete this file
	# Describe a Key: name, background, keycharon, keycharoff, label(string tuple), type (ONOFF,ONBlink,OnOffRun,?),addr,OnU,OffU

	pass

	"""
	if self.type == 'ONBLINKRUNTHEN':
		# deprecated parameter
		self.type = 'RUNTHEN'
		Blink = .5
	"""

	# for ONOFF keys (and others later) map the real and monitored nodes in the ISY
	# map the key to a scene or device - prefer to map to a scene so check that first
	# Obj is the representation of the ISY Object itself, addr is the address of the ISY device/scene



	def __repr__(self):
		return "KeyDesc:" + self.name + "|ST:" + str(self.State) + "|Clr:" + str(self.KeyColorOn) + "/" + str(
			self.KeyColorOff) + "|OnC:" + str(
			self.KeyCharColorOn) + "|OffC:" \
			   + str(self.KeyCharColorOff) + "\n\r        |Lab:" + str(
			self.label) + "|Typ:" + self.type + "|Px:" + \
			   "\n\r        |Ctr:" + str(self.Center) + "|Sz:" + str(self.Size)
