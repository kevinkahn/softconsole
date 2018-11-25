from stores import valuestore


class ParamStore(valuestore.ValueStore):
	def __init__(self, name, dp=None, locname=''):
		super(ParamStore, self).__init__(name)
		self.localname = locname if locname != '' else name
		self.children = {}
		self.defaultparent = dp
		if dp is not None:
			dp.MakeChild(self, self.localname)

	def GetVal(self, name):
		v = super(ParamStore, self).GetVal(name, failok=(self.defaultparent is not None))
		if v is None:
			return self.defaultparent.GetVal(name)
		else:
			return v

	def MakeChild(self, child, nm):
		self.children[nm] = child
