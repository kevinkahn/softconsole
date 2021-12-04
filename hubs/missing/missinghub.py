import logsupport
import stores.valuestore as valuestore
import stores.missinghubstore as missinghubstore


class DummyNode(object):
	def __init__(self, hubitem):
		self.state = -1
		self.name = 'Node Unavailable at Startup'
		self.Hub = hubitem
		self.address = '*none*'
		self.relatedstore = valuestore.NewValueStore(missinghubstore.MissingHubStore(hubitem.name, self))

	def SendOnOffCommand(self, st):
		return


class Hub(object):
	def __init__(self, hubname, addr, user, password, version):
		self.name = hubname
		self.addr = addr
		self.user = user
		self.password = password
		self.version = version
		self.DummyNode = DummyNode(self)
		self.alertspeclist = {}
		logsupport.Logs.Log('{}: Created as a dummy hub'.format(self.name))

	def GetNode(self, name, proxy=''):
		return self.DummyNode, self.DummyNode

	def GetProgram(self, name):
		return self.DummyNode

	def GetCurrentStatus(self, MonitorNode):
		return -1

	def AddToUnknowns(self, node):
		pass

	def DeleteFromUnknowns(self, node):
		pass

	def CheckStates(self):
		pass

	def SetAlertWatch(self, node, alert):
		pass  # done

	def StatesDump(self):
		logsupport.Logs.Log('{}: Call to dump states for a missing hub'.format(self.name))
