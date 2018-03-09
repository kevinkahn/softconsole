"""ss ValueStore(object):
	GetVal
	SetVsl
	AutoRefresh bool
	BlockRefresh
	LastBlockRefresh
"""
import config
from logsupport import ConsoleError, ConsoleWarning
import time

ValueStores = {} # General store for named values storename:itemname accessed as ValueStore[storename].GetVal(itemname)
				# or GetVal([itemname]) for a nested name


def NewValueStore(store):
	ValueStores[store.name] = store

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

	def GetVal(self,name):
		try:
			n2 = name[:] if isinstance(name,list) else [name]
			t = self.vars
			while n2 != []:
				t = t[n2[0]]
				n2.pop(0)
			if t.Expires + t.RcvTime < time.time():
				# value is stale
				return None
			else:
				return t.Value
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
