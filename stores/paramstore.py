from stores import valuestore


class ParamStore(valuestore.ValueStore):
	def __init__(self, name, dp=None):
		super(ParamStore, self).__init__(name)
		self.defaultparent = dp

	def GetVal(self, name):
		v = super(ParamStore, self).GetVal(name, failok=(self.defaultparent is not None))
		if v is None:
			return self.defaultparent.GetVal(name)
		else:
			return v
