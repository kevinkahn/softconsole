import debug
import xmltodict
from stores import valuestore
import isy


class ISYVars(valuestore.ValueStore):
	def __init__(self, name):
		super(ISYVars,self).__init__(name)

	def GetVal(self, name, forceactual=True):
		V =  super(ISYVars,self).GetVal(name)
		if forceactual == False:
			return V
		if V is None:
			# lazy load
			attr = self.GetAttr(name)
			text = isy.try_ISY_comm('/rest/vars/get/' + str(attr[0]) + '/' + str(attr[1]))  # todo what if notfound
			V = int(xmltodict.parse(text)['var']['val'])
			super(ISYVars, self).SetVal(name, V)
		return V

	def GetValByAttr(self, attr):
		V = super(ISYVars,self).GetValByAttr(attr)
		if V is None:
			text = isy.try_ISY_comm('/rest/vars/get/' + str(attr[0]) + '/' + str(attr[1]))  # todo what if notfound
			V = int(xmltodict.parse(text)['var']['val'])

	def BlockRefresh(self):

		for v in self.items():
			#print v, self.GetVal(v)
			self.GetVal(v)

	def CheckValsUpToDate(self):
		for v in self.items():
			goodcheck = True
			l = self.GetVal(v,forceactual=False)
			r = self.GetVal(v)
			if l != r:
				debug.debugPrint('StoreTrack','ISY Value Mismatch: (ISY) ',r,' (Local) ', l)
				goodcheck = False
		if goodcheck:
			debug.debugPrint('StoreTrack', 'ISY Value Check OK')


