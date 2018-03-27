from stores import valuestore
from configobj import Section

class LocalVars(valuestore.ValueStore):
	def __init__(self, name, configsect):
		super(LocalVars, self).__init__(name)
		id = 0
		for i, v in configsect.items():
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
				self.SetVal(i,tpv)
				self.SetType(i,tp)
				self.SetAttr(i,(3,id))
				id += 1
