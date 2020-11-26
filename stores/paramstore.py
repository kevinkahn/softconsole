import collections

from stores import valuestore
import logsupport
import random
from utils import exitutils


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
		if nm in self.children:
			rnd = random.randrange(1000)
			logsupport.Logs.Log(
				'Duplicate child store name {} within {} renamed {}'.format(nm, self.name, nm + str(rnd)),
				severity=logsupport.ConsoleWarning)
			nm = nm + str(rnd)
		self.children[nm] = child

	# noinspection PyProtectedMember
	def ReParent(self, newparent):
		try:
			del self.defaultparent.children[self.localname]
		except KeyError:
			logsupport.Logs.Log('Internal error attempt to reparent a duplicate named store {}'.format(self.localname),
								severity=logsupport.ConsoleError)
			exitutils.errorexit(exitutils.ERRORDIE)
		newparent.userstore._MakeChild(self, self.localname)
		self.defaultparent = newparent.userstore

	def DropStore(self):
		if self.localname in self.defaultparent.children: del self.defaultparent.children[self.localname]

	def __setattr__(self, key,
					value):  # todo this doesn't work as is - causes a recursion when GetVal is called via getattr
		if key in self.vars:
			self.SetVal(key, value)
		else:
			object.__setattr__(self, key, value)

	def __getattr__(self, key):
		return self.GetVal(key)

