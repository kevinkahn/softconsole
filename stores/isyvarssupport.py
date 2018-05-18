import debug
import xmltodict
from stores import valuestore


class ISYVars(valuestore.ValueStore):
	def __init__(self, thisisy):
		super(ISYVars,self).__init__(thisisy.name)
		self.isy = thisisy

	def GetVal(self, name, forceactual=True):
		V =  super(ISYVars,self).GetVal(name)
		if not forceactual:
			return V
		if V is None:
			# lazy load
			attr = self.GetAttr(name)
			text = self.isy.try_ISY_comm('vars/get/' + str(attr[0]) + '/' + str(attr[1]))
			if text != "":
				V = int(xmltodict.parse(text)['var']['val'])
				super(ISYVars, self).SetVal(name, V,
											modifier=True)  # don't reflect back to ISY - it just came from there
			else:
				V = -999999
		return V

	def GetValByAttr(self, attr):
		V = super(ISYVars,self).GetValByAttr(attr)
		if V is None: # why would val not be in attrlist of store already?
			text = self.isy.try_ISY_comm('vars/get/' + str(attr[0]) + '/' + str(attr[1]))
			if text != "":
				V = int(xmltodict.parse(text)['var']['val'])
			else:
				V = -999999
		return V

	def BlockRefresh(self):

		for v in self.items():
			#print v, self.GetVal(v)
			self.GetVal(v)

	def CheckValsUpToDate(self,reload=False):
		goodcheck = True
		for v in self.items():
			l = self.GetVal(v,forceactual=False)
			r = self.GetVal(v)
			if l != r:
				debug.debugPrint('StoreTrack','ISY Value Mismatch: (ISY) ',r,' (Local) ', l)
				goodcheck = False
		if goodcheck:
			debug.debugPrint('StoreTrack', 'ISY Value Check OK')


