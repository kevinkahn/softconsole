import config
from stores import valuestore
import time, hw


class SystemStore(valuestore.ValueStore):
	def __init__(self, name):
		super(SystemStore, self).__init__(name)

	def SetVal(self, name, val, modifier=None):
		# logsupport.Logs.Log("SysParam: ", valuestore.ExternalizeVarName(name),": ", val)
		super(SystemStore, self).SetVal(name, val, modifier=None)

	def GetVal(self, name, failok=False):
		t = self.HandleSpecial(name)
		if t is None:
			return super().GetVal(name, failok)
		else:
			return t

	def HandleSpecial(self, name):
		n = [name] if isinstance(name, str) else name
		if n[0] == 'Time':
			if len(n) == 1:
				return time.time()
			else:
				tf = n[1].replace('*',':')
				return time.strftime(tf)
		if n[0] == 'UpTime': return time.time() - self.GetVal(['ConsoleStartTime'])
		return None

	def __setattr__(self, key, value):
		if key in config.sysvals:
			self.SetVal(key, value)
		else:
			object.__setattr__(self, key, value)

	def __getattr__(self, key):
		return self.GetVal(key)
		#t = self.HandleSpecial(key)
		#if t is None:
		#	return self.GetVal(key)
		#else:
		#	return t
		#if key == 'Time': return time.time()
		#if key == 'UpTime': return time.time() - self.GetVal('ConsoleStartTime')
		#return self.GetVal(key)

