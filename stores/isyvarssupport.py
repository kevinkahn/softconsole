import time
from stores import valuestore


class ISYVarItem(valuestore.StoreItem):
	def __init__(self, id):
		self.id  = id
		self.RcvTime = 0
		self.Value = None

class ISYVars(valuestore.ValueStore):
	def __init__(self, name, vS, vI):
		self.name = name
		self.vars = {"State":{},"Int":{}}
		self.ids = {}
		for v in vS:
			self.vars["State"][v['@name']] = ISYVarItem(v['@id'])
			self.ids[(2,int(v['@id']))] = ('State',v['@name'])
		for v in vI:
			self.vars["Int"][v['@name']] = ISYVarItem(v['@id'])
			self.ids[(1,int(v['@id']))] = ('Int',v['@name'])

	def GetVal(self, name):  # make name a sequence ToDo use general seq code
		return self.vars[name[0]][name[1]].Value

	def GetValByID(self, id):
		return self.GetVal(self.ids[id])

	def SetVal(self, name, val):
		item = self.vars[name[0]][name[1]]
		item.Value = val
		item.RvcTime = time.time()


	def SetValByID(self, id, val):
		self.SetVal(self.ids[id], val)
