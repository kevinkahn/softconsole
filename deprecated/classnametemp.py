def do_save(cls):
	print
	cls
	cls.myname = "d" + cls.__name__
	cls.mycls = cls
	cls.test = "QQQ"
	print
	cls.__name__
	print
	cls.__doc__


class Atype(type):
	def __new__(meta, name, bases, dct):
		cls = super(Atype, meta).__new__(meta, name, bases, dct)
		do_save(cls)
		print
		"Class is ", meta.__name__
		meta.locname = meta.__name__
		return cls


class A(object):
	""" docstring """
	__metaclass__ = Atype
	myname = 'kkk'
	zz = 42

	def __init__(self):
		self.X = 'x'
		self.Y = 'y'
		print
		super(type(self))
		print
		"got here", self.__class__
		print
		"t1", A.myname
		print
		"t2", A.mycls
		print
		A.myname, ': ', self.__dict__
		print
		"L", locals()
		print
		"G", globals()


class B(A):
	def __init__(self):
		A.__init__(self)
		self.Z = 'x'
		print
		B.mycls
		print
		B.myname, self.__dict__
		print
		"L2", locals()
		print
		"G2", globals()


q = B()
