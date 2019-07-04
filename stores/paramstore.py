import collections

from stores import valuestore


class ParamStore(valuestore.ValueStore):
	# noinspection PyProtectedMember
	def __init__(self, name, dp=None, locname=''):
		super(ParamStore, self).__init__(name)
		self.localname = locname if locname != '' else name
		self.children = collections.OrderedDict()
		self.defaultparent = dp
		if dp is not None:
			dp._MakeChild(self, self.localname)

	def SetVal(self, name, val, modifier=None):
		if self.GetVal(name, failok=True) != val:
			super(ParamStore, self).SetVal(name, val, modifier)

	def GetVal(self, name, failok=False):
		v = super(ParamStore, self).GetVal(name, failok=(self.defaultparent is not None) or failok)
		if v is None and self.defaultparent is not None:
			return self.defaultparent.GetVal(name, failok)
		else:
			return v

	def _MakeChild(self, child, nm):
		self.children[nm] = child

	# noinspection PyProtectedMember
	def ReParent(self, newparent):
		del self.defaultparent.children[self.localname]
		newparent.userstore._MakeChild(self, self.localname)

	# def __setattr__(self, key, value):  todo this doesn't work as is - causes a recursion when GetVal is called via getattr
	#	if key in self.vars:
	#		self.SetVal(key, value)
	#	else:
	#		object.__setattr__(self, key, value)

	def __getattr__(self, key):
		return self.GetVal(key)
