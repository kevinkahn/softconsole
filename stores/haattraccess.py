from stores import valuestore
import logsupport
from logsupport import ConsoleError


class HAattributes(valuestore.ValueStore):
	def __init__(self, hubnm, hub):
		super().__init__(hubnm)
		self.hub = hub

	def _notallowed(self, procname):
		logsupport.Logs.Log('HA Attribute store {} does not permit {}'.format(self.hub.name, procname))
		raise AttributeError

	def AddAlert(self, name, a):
		if not self.Contains(name):
			self.SetVal(name, None)
			tn = self._normalizename(name)
			self.hub.MonitoredAttributes[tn[0]] = tn[1:]
		super().AddAlert(name, a)

	def GetVal(self, name, failok=False):
		# first try for an explicitly stored value (sensors)
		if self.Contains(name):
			val = super().GetVal(name, failok=True)
			return val

		# now try for a state or attribute
		n = self._normalizename(name)
		try:
			obj = self.hub.Entities[n[0]]
		except Exception as E:
			# no such entity - return error
			logsupport.Logs.Log('{} reference: Entity {} not defined in {} ({})'.format(name, n[0], self.hub.name, E),
								severity=ConsoleError)
			return None

		if len(n) == 1:
			# return state
			return obj.state
		else:
			# return attribute
			attr = obj.attributes
			# noinspection PyBroadException
			try:
				for i in n[1:]:
					attr = attr[i]
				return attr
			except Exception:
				# This is a normal case since attributes like brightness go undefined when state is off
				return None

	def SetType(self, name, vtype):
		self._notallowed('SetType')

	def SimpleInit(self, nmlist, init):
		self._notallowed('SimpleInit')

# what about the iterators, contains, items
