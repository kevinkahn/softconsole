from stores import valuestore
import logsupport
from logsupport import ConsoleError


class HAattributes(valuestore.ValueStore):
	def __init__(self, hubnm, hub):
		# self.name = hubnm todo del
		super().__init__(hubnm)
		self.hub = hub

	def _notallowed(self, procname):
		logsupport.Logs.Log('HA Attribute store {} does not permit {}'.format(self.name, procname))
		raise AttributeError

	def GetVal(self, name, failok=False):
		# first try for an explicitly stored value (sensors)
		val = super().GetVal(name, failok=True)
		if val is not None: return val

		# now try for a state or attribute
		n = self._normalizename(name)
		try:
			obj = self.hub.Entities[n[0]]
		except:
			# no such entity - return error
			logsupport.Logs.Log('{} reference: Entity {} not defined in {}'.format(name, n[0], self.hub.name),
								severity=ConsoleError)
			return None

		if len(n) == 1:
			# return state
			return obj.state
		else:
			# return attribute
			attr = obj.attributes
			try:
				for i in n[1:]:
					attr = attr[i]
				return attr
			except Exception as E:
				# This is a normal case since attributes like brightness go undefined when state is off
				return None

	def SetType(self, name, vtype):
		self._notallowed('SetType')

	def SimpleInit(self, nmlist, init):
		self._notallowed('SimpleInit')

# what about the iterators, contains, items
