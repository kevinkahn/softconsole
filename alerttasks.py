import config
from configobjects import Section
from collections import namedtuple

AlertItem = namedtuple('AlertItem', 'ToD, Interval, Device, Status, Var, Value')


class Alerts(object):
	def __init__(self, spec):
		if spec is not None:
			self.AlertItems = {}
			for nm, item in spec.items():
				if isinstance(item, Section):
					print nm, item
