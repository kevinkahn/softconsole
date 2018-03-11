import config
from logsupport import ConsoleError, ConsoleWarning
import time

ValueStores = {} # General store for named values storename:itemname accessed as ValueStore[storename].GetVal(itemname)
				# or GetVal([itemname]) for a nested name

def GetVal(name):
	return ValueStores[name[0]].GetVal(name[1:])

def BlockRefresh(name):
	ValueStores[name].BlockRefresh()

def NewValueStore(store):
	if store.name in ValueStores:
		if isinstance(ValueStores[store.name],type(store)):
			return ValueStores[store.name]
		else:
			config.Logs.Log("Incompatible store types for: "+store.name,severity=ConsoleError)
			return None
	else:
		ValueStores[store.name] = store
		return ValueStores[store.name]

class StoreItem(object):
	def __init__(self,initval,expires=9999999999999999):
		self.Value = initval
		self.Expires = expires
		self.RcvTime = time.time()

class ValueStore(object):
	def __init__(self, name, refreshinterval = 0):
		self.name = name
		self.fetchtime = 0 # time of last block refresh if handled as such
		self.refreshinterval = refreshinterval
		pass

	def GetVal(self,name): # todo make store properties accessible also
		try:
			if isinstance(name,tuple):
				n2 = list(name)
			elif isinstance(name,list):
				n2 = name[:]
			else:
				n2 = [name]
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
			if t.Expires + t.RcvTime < time.time():
				# value is stale
				return None
			else:
				return V
		except:
			config.Logs.Log("Error accessing ", self.name, ":", str(name), severity=ConsoleWarning)
			return None

	def GetValByID(self,id):
		config.Logs.Log("No value store GetValByID proc: ", self.name, severity=ConsoleError)

	def SetVal(self,name, val):
		config.Logs.Log("No value store SetVal proc: ", self.name, severity=ConsoleError)

	def SetValByID(self,id, val):
		config.Logs.Log("No value store SetValByID proc: ", self.name, severity=ConsoleError)

	def BlockRefresh(self):
		pass
