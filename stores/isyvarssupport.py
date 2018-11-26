import debug
import xmltodict
from stores import valuestore
import logsupport
from logsupport import ConsoleError


class ISYVars(valuestore.ValueStore):
	def __init__(self, thisisy):
		super(ISYVars,self).__init__(thisisy.name)
		self.isy = thisisy
		self.attrs = {}
		self.attrnames = {}

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

	def SetAttr(self, name, attr):
		# noinspection PyBroadException
		try:
			n = self._normalizename(name)
			item, index = self._accessitem(n)
			if index is None:
				if item.Attribute is None:
					item.Attribute = attr
					self.attrs[attr] = item
					self.attrnames[attr] = name
				else:
					logsupport.Logs.Log("Attribute already set for ", self.name, " new attr: ", attr)
			else:
				logsupport.Logs.Log("Can't set attribute on array element for ", self.name, " new attr: ", attr)
		except:
			logsupport.Logs.Log("Attribute setting error", self.name, " new attr: ", attr)

	def GetValByAttr(self, attr):
		V = self.attrs[attr].Value

		if V is None: # why would val not be in attrlist of store already?
			text = self.isy.try_ISY_comm('vars/get/' + str(attr[0]) + '/' + str(attr[1]))
			if text != "":
				V = int(xmltodict.parse(text)['var']['val'])
			else:
				V = -999999
		return V

	def GetNameFromAttr(self, attr):
		return self.attrs[attr].name

	def GetAttr(self, name):
		# noinspection PyBroadException
		try:
			n2 = self._normalizename(name)
			item, index = self._accessitem(n2)
			return item.Attribute
		except:
			logsupport.Logs.Log("Error accessing attribute ", self.name, ":", str(name), severity=ConsoleError)
			return None

	def SetValByAttr(self, attr, val, modifier=None):
		storeitem = self.attrs[attr]
		oldval = storeitem.Value
		storeitem.Value = val if storeitem.Type is None else storeitem.Type(val)
		for notify in storeitem.Alerts:
			notify[0](storeitem, oldval, val, notify[1], modifier)

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


