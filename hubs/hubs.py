hubtypes = {}
Hubs = {}
defaulthub = None  # move at least the name to sysStore todo other stuff should go to a __hubs.py file?


class HubInitError(Exception):
	pass


def HubLog(code, message=None):
	for hnm, h in Hubs.items():
		if hasattr(h, 'HubLog'):
			h.HubLog(code, message)
