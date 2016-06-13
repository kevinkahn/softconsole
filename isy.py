import collections

import xmltodict

import config
import utilities
import maintscreen
from config import ISYdebug
from logsupport import ConsoleInfo, ConsoleWarning, ConsoleError


def get_real_time_status(addrlist):
	# multiple calls here is substantially faster than one call for all status then selecting devices
	# this proc assumes a device that returns a simple ST value for status
	statusdict = {}
	for addr in addrlist:
		try:
			r = config.ISYrequestsession.get('http://' + config.ISYaddr + '/rest/status/' + addr, verify=False)
		except:
			config.Logs.Log("ISY Comm Error (realtime status)" + addr, severity=ConsoleError)
			maintscreen.errorexit('reboot')
		props = xmltodict.parse(r.text)['properties']['property']
		if isinstance(props, dict):
			props = [props]
		devstate = 0
		for item in props:
			if item['@id'] == "ST":
				devstate = item['@value']
				break
		statusdict[addr] = int(devstate if devstate.isdigit() else 0)
	return statusdict


class TreeItem(object):
	"""
	Provides the graph structure for the ISY representation.  Any ISY node can have a parent and children managed by
	this class.  The class also holds identity information, namely name and addr
	"""

	def __init__(self, name, addr, parentaddr):
		self.name = name
		self.address = addr
		self.parent = parentaddr  # replaced by actual obj reference at end of tree build
		self.children = []
		utilities.register_example("TreeItem", self)

	def __repr__(self):
		return 'Tree Iten: ' + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children'


class OnOffItem(object):
	"""
	Provides command handling for nodes that can be sent on/off faston/fastoff commands.
	"""

	def SendCommand(self, state, fast):
		selcmd = (('DOF', 'DFOF'), ('DON', 'DFON'))
		config.debugPrint('ISY', "OnOff sent: ", selcmd[state][fast], ' to ', self.name)
		url = 'http://' + config.ISYaddr + '/rest/nodes/' + self.address + '/cmd/' + selcmd[state][fast]
		r = config.ISYrequestsession.get(url)
		return r


class Folder(TreeItem):
	"""
	Represents and ISY node/scene folder.
	"""

	def __init__(self, flag, name, addr, parenttyp, parentaddr):
		TreeItem.__init__(self, name, addr, parentaddr)
		self.flag = flag
		self.parenttype = parenttyp
		utilities.register_example("Folder", self)

	def __repr__(self):
		return "Folder: " + TreeItem.__repr__(self) + ' flag ' + str(self.flag) + ' parenttyp ' + str(self.parenttype)


class Node(Folder, OnOffItem):
	"""
	Represents and ISY device node.
	"""

	def __init__(self, flag, name, addr, parenttyp, parentaddr, enabled, props):
		Folder.__init__(self, flag, name, addr, parenttyp, parentaddr)
		self.pnode = None  # for things like KPLs
		self.enabled = enabled == "true"
		self.hasstatus = False
		# props is either an OrderedDict(@id:ST,@value:val, . . .) or a list of such
		if isinstance(props, collections.OrderedDict):
			props = [props]  # make it a list so below always works
		for item in props:
			if item['@id'] == 'ST':
				if item['@value'] <> ' ':
					self.hasstatus = True
				# no use for nodetype now
				# device class -energy management
				# wattage, dcPeriod
		utilities.register_example("Node", self)

	def __repr__(self):
		return 'Node: ' + Folder.__repr__(self) + 'primary: ' + self.pnode.name


class Scene(TreeItem, OnOffItem):
	"""
	Represents an ISY scene.
	"""

	def __init__(self, flag, name, addr, parenttyp, parent, members):
		"""

		:rtype: Scene
		"""
		TreeItem.__init__(self, name, addr, parent)
		self.flag = flag
		self.parenttype = parenttyp
		# self.devGroup = devGroup
		self.members = members
		self.proxy = ""
		self.obj = None
		utilities.register_example("Scene", self)

	def __repr__(self):
		return "Scene: " + TreeItem.__repr__(self) + ' ' + str(
			len(self.members)) + ' members: ' + self.members.__repr__()


class ProgramFolder(TreeItem):
	"""
	Represents an ISY program folder (ISY keeps the node and program folders separately)
	"""

	def __init__(self, nm, itemid, pid):
		TreeItem.__init__(self, nm, itemid, pid)
		self.status = False
		# not using lastRunTime, lastFinishTime
		utilities.register_example("ProgramFolder", self)

	def __repr__(self):
		return 'ProgFolder: ' + TreeItem.__repr__(self) + ' status ' + str(self.status)


class Program(ProgramFolder):
	"""
	Represents an ISY program and provides command support to issue run commands to it.
	"""

	def __init__(self, nm, itemid, pid):
		ProgramFolder.__init__(self, nm, itemid, pid)
		# not using enabled, runAtStartup,running
		utilities.register_example("Program", self)

	def runThen(self):
		config.debugPrint('ISY', "runThen sent to ", self.name)
		url = config.ISYprefix + 'programs/' + self.address + '/runThen'
		r = config.ISYrequestsession.get(url)
		return r

	def __repr__(self):
		return 'Program: ' + TreeItem.__repr__(self) + ' '


class ISY(object):
	"""
	Singleton object (1 per console) that represents the ISY system as a whole and provides roots to its structures
	and useful directories to its nodes/programs.  Provides a debug method to dump the constructed graph.
	Note current limitation: assumes non-conflicting names at the leaves.  Qualified name support is a future addition.
	"""

	@staticmethod
	def LinkChildrenParents(nodelist, listbyname, looklist1, looklist2):

		for node in nodelist.itervalues():
			listbyname[node.name] = node
			if node.parent in looklist1:
				node.parent = looklist1[node.parent]  # replace address with actual object
			elif node.parent in looklist2:
				node.parent = looklist2[node.parent]
			else:
				node.parent = None
				config.Logs.Log("Missing parent: " + node.name, severity=ConsoleError)
			if node.parent <> node:  # avoid root
				node.parent.children.append(node)

	def __init__(self, ISYsession):
		"""
		Get and parse the ISY configuration to set up an internal analog of its structure
		:param ISYsession:
		:return:
		"""

		self.NodeRoot = Folder(0, '*root*', u'0', 0, u'0')
		self.ProgRoot = None
		self.NodesByAddr = {}
		self.FoldersByAddr = {'0': self.NodeRoot}
		self.ScenesByAddr = {}
		self.NodesByName = {}
		self.ScenesByName = {}
		self.FoldersByName = {}
		self.ProgramFoldersByAddr = {}
		self.ProgramsByAddr = {}
		self.ProgramsByName = {}
		self.ProgramFoldersByName = {}

		"""
		Build the Folder/Node/Scene tree
		"""

		r = ISYsession.get(config.ISYprefix + 'nodes', verify=False)
		configdict = xmltodict.parse(r.text)['nodes']

		for folder in configdict['folder']:
			addr = folder['address']
			parentaddr = str(0)
			ptyp = 3
			if 'parent' in folder:
				ptyp = int(folder['parent']['@type'])
				parentaddr = folder['parent']['#text']
			self.FoldersByAddr[addr] = Folder(folder['@flag'], folder['name'], str(addr), ptyp, parentaddr)
		self.LinkChildrenParents(self.FoldersByAddr, self.FoldersByName, self.FoldersByAddr, self.NodesByAddr)

		fixlist = []
		for node in configdict['node']:
			parentaddr = str(0)
			ptyp = 3
			if 'parent' in node:
				ptyp = int(node['parent']['@type'])
				parentaddr = node['parent']['#text']
			try:
				n = Node(node['@flag'], node['name'], node['address'], ptyp, parentaddr, node['enabled'], node['property'])
				fixlist.append((n, node['pnode']))
				self.NodesByAddr[n.address] = n
			except:
				pass # for now at least try to avoid nodes without properties which apparently Zwave devices may have
		self.LinkChildrenParents(self.NodesByAddr, self.NodesByName, self.FoldersByAddr, self.NodesByAddr)
		for fixitem in fixlist:
			fixitem[0].pnode = self.NodesByAddr[fixitem[1]]

		for scene in configdict['group']:
			memberlist = []
			if scene['members'] is not None:
				m1 = scene['members']['link']
				if isinstance(m1, list):
					for m in m1:
						memberlist.append((int(m['@type']), self.NodesByAddr[m['#text']]))
				else:
					memberlist.append((int(m1['@type']), self.NodesByAddr[m1['#text']]))
				if 'parent' in scene:
					ptyp = int(scene['parent']['@type'])
					p = scene['parent']['#text']
				else:
					ptyp = 0
					p = '0'
				self.ScenesByAddr[scene['address']] = Scene(scene['@flag'], scene['name'], str(scene['address']), ptyp,
															p, memberlist)
			else:
				if scene['name'] <> '~Auto DR':
					print 'Scene with no members', scene['name']
		self.LinkChildrenParents(self.ScenesByAddr, self.ScenesByName, self.FoldersByAddr, self.NodesByAddr)
		if ISYdebug:
			self.PrintTree(self.NodeRoot, "    ")

		"""
		Build the Program tree
		"""

		r = ISYsession.get(config.ISYprefix + 'programs?subfolders=true', verify=False)
		configdict = xmltodict.parse(r.text)['programs']['program']
		for item in configdict:
			if item['@id'] == '0001':
				# Program Root
				self.ProgRoot = ProgramFolder(item['name'], '0001', '0001')
				self.ProgramFoldersByAddr['0001'] = self.ProgRoot
			else:
				if item['@folder'] == 'true':
					self.ProgramFoldersByAddr[item['@id']] = ProgramFolder(item['name'], item['@id'], item['@parentId'])
				else:
					self.ProgramsByAddr[item['@id']] = Program(item['name'], item['@id'], item['@parentId'])
		self.LinkChildrenParents(self.ProgramFoldersByAddr, self.ProgramFoldersByName, self.ProgramFoldersByAddr,
								 self.ProgramsByAddr)
		self.LinkChildrenParents(self.ProgramsByAddr, self.ProgramsByName, self.ProgramFoldersByAddr,
								 self.ProgramsByAddr)

		utilities.register_example("ISY", self)
		if ISYdebug:
			self.PrintTree(self.ProgRoot, "    ")

	def PrintTree(self, startpoint, indent):
		if isinstance(startpoint, Scene):
			print indent + startpoint.__repr__()
			for m in startpoint.members:
				if m[0] == 16:
					sR = 'R'
				elif m[0] == 32:
					sR = 'C'
				else:
					sR = 'X'
				print indent + "-" + sR + "--" + (m[1].__repr__())
		elif isinstance(startpoint, TreeItem):
			print indent + startpoint.__repr__()
			for c in startpoint.children:
				self.PrintTree(c, indent + "....")
		else:
			print "Funny thing in tree ", startpoint.__repr__
