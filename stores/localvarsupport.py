from stores import valuestore
from configobj import Section

class LocalVarItem(valuestore.StoreItem):
	def __init__(self, id, tpcvrt, initval):
		super(LocalVarItem,self).__init__(initval)
		self.id  = id
		self.VarType = tpcvrt

class LocalVars(valuestore.ValueStore):
	def __init__(self, name, configsect):
		self.name = name
		self.vars = {}
		self.ids = {}
		id = 0
		for i, v in configsect.iteritems():
			if isinstance(v, Section):
				tp = v.get('VarType', 'int')
				if tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				elif tp == 'bool':
					tpcvrt = bool
				else:
					tpcvrt = str
				tpv = v.get('Value', None)
				self.vars[i] = LocalVarItem(id, tpcvrt, tpv)  # todo pub?
				self.ids[id] = i
				id += 1

	def GetValByID(self, id):
		return self.GetVal(self.ids[id])

#	def SetVal(self, name, val):
#		item = self.vars[name[0]][name[1]]
#		item.Value = val
#		item.RvcTime = time.time()


	def SetValByID(self, id, val):
		self.SetVal(self.ids[id], val)
