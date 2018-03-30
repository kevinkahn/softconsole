from stores import valuestore
# noinspection PyProtectedMember
from configobj import Section

class LocalVars(valuestore.ValueStore):
	def __init__(self, name, configsect):
		super(LocalVars, self).__init__(name)
		lclid = 0
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
				self.SetType(i,tpcvrt)
				self.SetAttr(i,(3,lclid))
				lclid += 1
