from logsupport import ConsoleError
import logsupport
import time

ValueStores = {} # General store for named values storename:itemname accessed as ValueStore[storename].GetVal(itemname)
				# or GetVal([itemname]) for a nested name

def GetVal(name):
	return ValueStores[name[0]].GetVal(name[1:])

def SetVal(name,val, attribute=None):
	return ValueStores[name[0]].SetVal(name[1:],val)

#todo getAttr(name) getbyAttr(attr) gets value, name

def BlockRefresh(name):
	ValueStores[name].BlockRefresh()

def NewValueStore(store):
	if store.name in ValueStores:
		if isinstance(ValueStores[store.name],type(store)):
			return ValueStores[store.name]
		else:
			logsupport.Logs.Log("Incompatible store types for: "+store.name,severity=ConsoleError)
			return None
	else:
		ValueStores[store.name] = store
		return ValueStores[store.name]

class StoreItem(object):
	def __init__(self, name, initval, vt = None, expires=9999999999999999.0, attribute=None):
		self.Value = initval
		self.Type = type(initval) if vt == None else vt
		self.Expires = expires
		self.SetTime = time.time()
		self.Attribute = attribute
		self.name = name

	def UpdateVal(self,val):
		self.Value = self.Type(val)
		self.SetTime = time.time()

	def UpdateArrayVal(self,index,val):
		if isinstance(self.Value, list):
			if index >= len(self.Value):
				for i in range(len(self.Value),index+1):
					self.Value.append(None)
			self.Value[index] = val
		else:
			return # todo error
		self.SetTime = time.time()

class ValueStore(object):
	def __init__(self, name, refreshinterval = 0, itemtyp=StoreItem):
		self.name = name
		self.itemtyp = itemtyp
		self.fetchtime = 0 # time of last block refresh if handled as such
		self.refreshinterval = refreshinterval


	def _normalizename(self,name):
		if isinstance(name, tuple):
			return list(name)
		elif isinstance(name, list):
			return name[:]
		else:
			return [name]

	def GetVal(self,name):
		if self.refreshinterval != 0 and time.time()>self.fetchtime+self.refreshinterval:
			self.BlockRefresh()
		try:
			n2 = self._normalizename(name)
			t = self.vars
			while len(n2) > 1:
				t = t[n2[0]]
				n2.pop(0)
			if isinstance(n2[0], int):
				# final is array
				V = t.Value[n2[0]]
			else:
				t = t[n2[0]]
				V = t.Value
			if t.Expires + t.SetTime < time.time():
				# value is stale
				return None
			else:
				return V
		except:
			logsupport.Logs.Log("Error accessing ", self.name, ":", str(name), severity=ConsoleError)
			return None

	def SimpleInit(self, nmlist, typ, init):
		if self.itemtyp != StoreItem:
			logsupport.Logs.Log("Can't SimpleInit non-simple store: ",self.name, severity=ConsoleError)
			return # todo abort internal error
		if isinstance(nmlist, tuple) or isinstance(nmlist, list):
			self.vars = {}
			for n in nmlist:
				self.vars[n] = self.itemtyp(n,init,typ)

	def SetVal(self,name, val):
		n2 = self._normalizename(name)
		t = self.vars
		while len(n2) > 1:
			if n2[0] in t:
				t = t[n2[0]]
				n2.pop(0)
			else:
				t[n2[0]] = {} if not isinstance(n2[1],int) else self.itemtyp([])
				t = t[n2[0]]
				n2.pop(0)
		if isinstance(n2[0], int):
			if isinstance(t,self.itemtyp):
				t.UpdateArrayVal(n2[0],val)
			elif isinstance(t,dict):
				t = self.itemtyp([])
				t.UpdateArrayVal(n2[0],val)
		else:
			if n2[0] in t:
				# already exists
				t[n2[0]].UpdateVal(val)
			else:
				t[n2[0]] = self.itemtyp(name,val)

	def Contains(self,name):
		n2 = self._normalizename(name)
		t = self.vars
		try:
			while len(n2) > 1:
				t = t[n2[0]]
				n2.pop(0)
			if isinstance(n2[0], int):
				# final is array
				return True if n2[0] < len(t.Value) else False
			else:
				return True if n2[0] in t else False
		except:
			return False

	def BlockRefresh(self):
		pass
