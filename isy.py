import collections

import xmltodict
import requests, time
import config
import debug
import exitutils
import utilities
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetailHigh
import sys
import errno
import pygame
from stores import valuestore, isyvarssupport


class CommsError(Exception): pass

def check_ISY_comm():
	urlcmd = '/rest/time'
	if config.ISYaddr.startswith('http'):
		t = config.ISYaddr + urlcmd
	else:
		t = 'http://' + config.ISYaddr + urlcmd
	try:
		r = config.ISYrequestsession.get(t, verify=False, timeout=5)
	except requests.exceptions.ConnectionError as e:
		return e[0]
	return 0

def try_ISY_comm(urlcmd):
	for i in range(15):
		try:
			try:
				if config.ISYaddr.startswith('http'):
					t = config.ISYaddr + urlcmd
				else:
					t = 'http://' + config.ISYaddr + urlcmd
				debug.debugPrint('ISY', '*' + t + '*')
				r = config.ISYrequestsession.get(t, verify=False, timeout=5)
			except requests.exceptions.ConnectTimeout as e:
				logsupport.Logs.Log("ISY Comm Timeout: " + ' Cmd: ' + '*' + urlcmd + '*', severity=ConsoleError, tb=False)
				logsupport.Logs.Log(sys.exc_info()[1], severity=ConsoleDetailHigh, tb=False)
				raise CommsError
			except requests.exceptions.ConnectionError as e:
				try:
					if e[0] == errno.ENETUNREACH:
						# probable network outage for reboot
						logsupport.Logs.Log("ISY Comm: Network Unreachable", tb=False)
						time.sleep(120)
					else:
						logsupport.Logs.Log("ISY Comm ConnErr: " + ' Cmd: ' + urlcmd, severity=ConsoleError, tb=False)
						logsupport.Logs.Log(sys.exc_info()[1], severity=ConsoleDetailHigh, tb=False)
				except:
					logsupport.Logs.Log("ISY Comm ConnErr2: " + ' Cmd: ' + urlcmd, severity=ConsoleError, tb=False)
					logsupport.Logs.Log(sys.exc_info()[1], severity=ConsoleDetailHigh, tb=False)
				raise CommsError
			except Exception as e:
				logsupport.Logs.Log("ISY Comm UnknownErr: " + ' Cmd: ' + urlcmd, severity=ConsoleError)
				logsupport.Logs.Log("  Exception: ",str(e))
				logsupport.Logs.Log(sys.exc_info()[1], severity=ConsoleDetailHigh, tb=True)
				raise CommsError
			if r.status_code == 404: # not found
				return 'notfound'
			if r.status_code != 200:
				logsupport.Logs.Log('ISY Bad status:' + str(r.status_code) + ' on Cmd: ' + urlcmd, severity=ConsoleError)
				logsupport.Logs.Log(r.text)
				raise CommsError
			else:
				return r.text
		except CommsError:
			time.sleep(.5)
			logsupport.Logs.Log("Attempting ISY retry " + str(i + 1), severity=ConsoleError, tb=False)

	logsupport.Logs.Log("ISY Communications Failure", severity=ConsoleError)
	exitutils.errorexit(exitutils.ERRORPIREBOOT)


def get_real_time_obj_status(obj):
	if obj is not None:
		return get_real_time_node_status(obj.address)
	else:
		return 0


def get_real_time_node_status(addr):
	if addr == '':
		return 0  # allow for missing ISY
	text = try_ISY_comm('/rest/status/' + addr)  # todo what if notfound?
	props = xmltodict.parse(text)['properties']['property']
	if isinstance(props, dict):
		props = [props]
	devstate = 0
	for item in props:
		if item['@id'] == "ST":
			devstate = item['@value']
			break
	try:
		if config.ISY.NodesByAddr[addr].devState != int(devstate):
			logsupport.Logs.Log("Shadow state wrong: ", addr, devstate, config.ISY.NodesByAddr[addr].devState,
							severity=ConsoleWarning)
	except:
		logsupport.Logs.Log('Bad NodeByAddr in rt status: ', addr, severity=ConsoleError)
	return int(devstate if devstate.isdigit() else 0)


class TreeItem(object):
	"""
	Provides the graph structure for the ISY representation.  Any ISY node can have a parent and children managed by
	this class.  The class also holds identity information, namely name and addr
	"""

	def __init__(self, name, addr, parentaddr):
		self.fullname = ""
		self.name = name
		self.address = addr
		self.parent = parentaddr  # replaced by actual obj reference at end of tree build
		self.children = []
		utilities.register_example("TreeItem", self)

	def __repr__(self):
		return 'Tree Item: ' + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children'


class OnOffItem(object):
	"""
	Provides command handling for nodes that can be sent on/off faston/fastoff commands.
	"""

	def SendCommand(self, state, presstype):
		selcmd = (('DOF', 'DFOF'), ('DON', 'DFON'))
		debug.debugPrint('ISY', "OnOff sent: ", selcmd[state][presstype], ' to ', self.name)
		text = try_ISY_comm('/rest/nodes/' + self.address + '/cmd/' + selcmd[state][presstype])


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
		self.devState = -1  # device status reported in the ISY event stream
		# props is either an OrderedDict(@id:ST,@value:val, . . .) or a list of such
		if isinstance(props, collections.OrderedDict):
			props = [props]  # make it a list so below always works
		for item in props:
			if item['@id'] == 'ST':
				if item['@value'] != ' ':
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
		debug.debugPrint('ISY', "runThen sent to ", self.name)
		url = config.ISYprefix + 'programs/' + self.address + '/runThen'
		r = config.ISYrequestsession.get(url)
		return r

	def __repr__(self):
		return 'Program: ' + TreeItem.__repr__(self) + ' '


def GetVar(var):
	if var[0] == 3:  # Local var
		return config.ISY.LocalVars[var[1]]
	elif var[0] == 0:  # non-existent reference
		return 999
	else:
		text = try_ISY_comm('/rest/vars/get/' + str(var[0]) + '/' + str(var[1])) # todo what if notfound
		val = int(xmltodict.parse(text)['var']['val'])
		valuestore.SetValByAttr('ISY',var,val) #todo eventually make this pick up name from the hub name
		return val


def SetVar(var, value):  # todo convert local to store model with alert; use attr of local as notice info but how to set notice and what if more than one cares
	if var[0] == 3:
		config.ISY.LocalVars[var[1]] = value
		if tuple(var) in config.DS.WatchVars.keys():
			config.DS.WatchVarVals[var[0], var[1]] = value

			for a in config.DS.WatchVars[tuple(var)]:
				logsupport.Logs.Log("Var alert fired: " + str(a))
				notice = pygame.event.Event(config.DS.ISYVar, vartype=var[0], varid=var[1], value=value, alert=a)
				pygame.fastevent.post(notice)

	else:
		try_ISY_comm('/rest/vars/set/' + str(var[0]) + '/' + str(var[1]) + '/' + str(value)) # todo what if notfound


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
				logsupport.Logs.Log("Missing parent: " + node.name, severity=ConsoleError)
			if node.parent != node:  # avoid root
				node.parent.children.append(node)

	def __init__(self, ISYsession, ISYname='ISY'):
		"""
		Get and parse the ISY configuration to set up an internal analog of its structure
		:param ISYsession:
		:return:
		"""

		self.NodeRoot = Folder(0, '', u'0', 0, u'0') # *root*
		self.ProgRoot = None
		self.NodesByAddr = {}
		self.FoldersByAddr = {'0': self.NodeRoot}
		self.ScenesByAddr = {}
		self.NodesByName = {}
		self.NodesByFullName = {}
		self.ScenesByName = {}
		self.FoldersByName = {}
		self.ProgramFoldersByAddr = {}
		self.ProgramsByAddr = {}
		self.ProgramsByName = {}
		self.ProgramFoldersByName = {}
		self.varsState = {}
		self.varsStateInv = {}
		self.varsInt = {}
		self.varsIntInv = {}
		self.varsLocal = {}
		self.varsLocalInv = {}
		self.LocalVars = []

		if ISYsession is None:
			# No ISY provided return empty structure
			return

		"""
		Build the Folder/Node/Scene tree
		"""

		trycount = 20
		while True:
			try:
				r = ISYsession.get(config.ISYprefix + 'nodes', verify=False, timeout=5)
				logsupport.Logs.Log('Successful node read: ' + str(r.status_code))
				break
			# except requests.exceptions.ConnectTimeout:
			except:
				# after total power outage ISY is slower to come back than RPi so
				# we wait testing periodically.  Eventually we try rebooting just in case our own network
				# is what is hosed
				trycount -= 1
				if trycount > 0:
					logsupport.Logs.Log('ISY not responding')
					logsupport.Logs.Log('-ISY (nodes): ' + config.ISYprefix)
					time.sleep(15)
				else:
					logsupport.Logs.Log('No ISY response restart (nodes)')
					exitutils.errorexit(exitutils.ERRORPIREBOOT)
					logsupport.Logs.Log('Reached unreachable code! ISY1')

		if r.status_code != 200:
			logsupport.Logs.Log('ISY text response:', severity=ConsoleError)
			logsupport.Logs.Log('-----', severity=ConsoleError)
			logsupport.Logs.Log(r.text, severity=ConsoleError)
			logsupport.Logs.Log('-----', severity=ConsoleError)
			logsupport.Logs.Log('Cannot access ISY - check username/password')
			logsupport.Logs.Log('Status code: ' + str(r.status_code))
			time.sleep(10)
			exitutils.errorexit(exitutils.ERRORDIE)
			logsupport.Logs.Log('Reached unreachable code! ISY2')

		configdict = xmltodict.parse(r.text)['nodes']
		if debug.dbgStore.GetVal('ISYLoad'):
			with open('/home/pi/Console/xml.dmp','r') as f:
				x1 = f.readline().rstrip('\n')
				x2 = f.readline().rstrip('\n')
				x3 = f.readline().rstrip('\n')
				x4 = f.readline().rstrip('\n')
				configdict = xmltodict.parse(x1)['nodes']
		else:
			x2=''
			x3=''
			x4=''

		if debug.dbgStore.GetVal('ISYDump'):
			debug.ISYDump("xml.dmp",r.text,pretty=False,new=True)
			debug.ISYDump("struct.dmp",configdict,new=True)
			debug.ISYDump("isystream.dmp","",pretty=False,new=True)

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
				flg = 'unknown'
				nm = 'unknown'
				addr = 'unknown'
				enabld = 'unknown'
				prop = 'unknown'
				pnd = 'unknown'
			try:
				flg = node['@flag']
				nm = node['name']
				addr = node['address']
				enabld = node['enabled']
				pnd = node['pnode']
				prop = node['property']
				n = Node(flg, nm, addr, ptyp, parentaddr, enabld, prop)
				fixlist.append((n, pnd))
				self.NodesByAddr[n.address] = n
			except:
				logsupport.Logs.Log("Problem with processing node: ", nm, ' Address: ', str(addr), ' Pnode: ', str(pnd),
								' ', str(flg), '/', str(enabld), '/', repr(prop), severity=ConsoleWarning)
				# for now at least try to avoid nodes without properties which apparently Zwave devices may have
		self.LinkChildrenParents(self.NodesByAddr, self.NodesByName, self.FoldersByAddr, self.NodesByAddr)
		for fixitem in fixlist:
			try:
				fixitem[0].pnode = self.NodesByAddr[fixitem[1]]
			except:
				logsupport.Logs.Log("Problem with processing node: ", fixitem[1], severity=ConsoleWarning)

		for scene in configdict['group']:
			memberlist = []
			if scene['members'] is not None:
				m1 = scene['members']['link']
				try:
					if isinstance(m1, list):
						for m in m1:
							naddr = m['#text']
							memberlist.append((int(m['@type']), self.NodesByAddr[naddr]))
					else:
						naddr = m1['#text']
						memberlist.append((int(m1['@type']), self.NodesByAddr[naddr]))
				except:
					logsupport.Logs.Log("Error adding member to scene: ", str(scene['name']), ' Node address: ', naddr, severity=ConsoleWarning)
					debug.debugPrint('ISYDump','Scene: ',m1)

				if 'parent' in scene:
					ptyp = int(scene['parent']['@type'])
					p = scene['parent']['#text']
				else:
					ptyp = 0
					p = '0'
				self.ScenesByAddr[scene['address']] = Scene(scene['@flag'], scene['name'], str(scene['address']), ptyp,
															p, memberlist)
			else:
				if scene['name'] not in ('~Auto DR', 'Auto DR'):
					logsupport.Logs.Log('Scene with no members ', scene['name'], severity=ConsoleWarning)
		self.LinkChildrenParents(self.ScenesByAddr, self.ScenesByName, self.FoldersByAddr, self.NodesByAddr)

		self.SetFullNames(self.NodeRoot,"")

		if debug.dbgStore.GetVal('ISY'):
			self.PrintTree(self.NodeRoot, "    ", 'Nodes')

		"""
		Build the Program tree
		"""

		trycount = 20
		while True:
			try:
				r = ISYsession.get(config.ISYprefix + 'programs?subfolders=true', verify=False, timeout=5)
				if r.status_code != 200:
					logsupport.Logs.Log('ISY bad program read' + r.text, severity=ConsoleWarning)
					raise requests.exceptions.ConnectionError  # fake a connection error if we didn't get a good read
				logsupport.Logs.Log('Successful programs read: ' + str(r.status_code))
				break
			# except requests.exceptions.ConnectTimeout:
			except:
				# after total power outage ISY is slower to come back than RPi sowait testing periodically.
				# Eventually we try rebooting just in case our own network is what is hosed
				trycount -= 1
				if trycount > 0:
					logsupport.Logs.Log('ISY not responding')
					logsupport.Logs.Log('-ISY(programs): ' + config.ISYprefix)
					time.sleep(15)
				else:
					logsupport.Logs.Log('No ISY response restart (programs)')
					exitutils.errorexit(exitutils.ERRORPIREBOOT)
					logsupport.Logs.Log('Reached unreachable code! ISY3')
		configdict = xmltodict.parse(r.text)['programs']['program']
		if debug.dbgStore.GetVal('ISYLoad'):
			configdict = xmltodict.parse(x2)['programs']['program']
		if debug.dbgStore.GetVal('ISYDump'):
			debug.ISYDump("xml.dmp",r.text,pretty=False)
			debug.ISYDump("struct.dmp",configdict)

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
		config.DummyProgram = Program('dummy', 0, 0)

		def Noop():
			debug.debugPrint('Main', "Dummy program invocation")
			pass

		config.DummyProgram.runThen = Noop

		"""
		Get the variables
		"""
		while True:
			try:
				r1 = ISYsession.get(config.ISYprefix + 'vars/definitions/2', verify=False, timeout=5)
				r2 = ISYsession.get(config.ISYprefix + 'vars/definitions/1', verify=False, timeout=5)
				# for some reason var reads seem to typically take longer to complete so to at 5 sec
				if r1.status_code != 200 or r2.status_code != 200:
					logsupport.Logs.Log("Bad ISY var read" + r1.text + r2.text, severity=ConsoleWarning)
					raise requests.exceptions.ConnectionError  # fake connection error on bad read
				logsupport.Logs.Log('Successful variable read: ' + str(r1.status_code) + '/' + str(r2.status_code))
				break
			except:
				# after total power outage ISY is slower to come back than RPi so we wait testing periodically
				# Eventually we try rebooting just in case our own network is what is hosed
				trycount -= 1
				if trycount > 0:
					logsupport.Logs.Log('ISY not responding')
					logsupport.Logs.Log('-ISY(vars): ' + config.ISYprefix)
					time.sleep(15)
				else:
					logsupport.Logs.Log('No ISY response restart (vars)')
					exitutils.errorexit(exitutils.ERRORPIREBOOT)
					logsupport.Logs.Log('Reached unreachable code! ISY4')

		Vars = valuestore.NewValueStore(isyvarssupport.ISYVars(ISYname))
		try:
			configdictS = xmltodict.parse(r1.text)['CList']['e']
			if debug.dbgStore.GetVal('ISYLoad'):
				configdictS = xmltodict.parse(x3)['CList']['e']
			if debug.dbgStore.GetVal('ISYDump'):
				debug.ISYDump("xml.dmp", r1.text, pretty=False)
				debug.ISYDump("struct.dmp", configdictS)
			for v in configdictS:
				Vars.SetVal(('State',v['@name']),None)
				Vars.SetAttr(('State',v['@name']),(2,int(v['@id'])))
				self.varsState[v['@name']] = int(v['@id'])
				self.varsStateInv[int(v['@id'])] = v['@name']
		except:
			self.varsState['##nostatevars##'] = 0
			logsupport.Logs.Log('No state variables defined')
		try:
			configdictI = xmltodict.parse(r2.text)['CList']['e']
			if debug.dbgStore.GetVal('ISYLoad'):
				configdictI = xmltodict.parse(x4)['CList']['e']
			if debug.dbgStore.GetVal('ISYDump'):
				debug.ISYDump("xml.dmp", r2.text, pretty=False)
				debug.ISYDump("struct.dmp", configdictI)
			for v in configdictI:
				Vars.SetVal(('Int',v['@name']),None)
				Vars.SetAttr(('Int',v['@name']),(1,int(v['@id'])))
				self.varsInt[v['@name']] = int(v['@id'])
				self.varsIntInv[int(v['@id'])] = v['@name']
		except:
			self.varsInt['##nointevars##'] = 0
			logsupport.Logs.Log('No integer variables defined')
		utilities.register_example("ISY", self)
		if debug.dbgStore.GetVal('ISY'):
			self.PrintTree(self.ProgRoot, "    ", 'Programs')

	def GetVarCode(self, varsym):
		try:
			if varsym[0] == 'I':  # int var
				return 1, self.varsInt[varsym[1]]
			elif varsym[0] == 'S':  # state var
				return 2, self.varsState[varsym[1]]
			elif varsym[0] == 'L':  # local var  todo change to store reference to LocalVar:
				return 3, self.varsLocal[varsym[1]]
			return 0, 0
		except:
			return 0, 0

	def SetFullNames(self, startpoint, parentname):
		startpoint.fullname = parentname + startpoint.name
		self.NodesByFullName[startpoint.fullname] = startpoint
		if isinstance(startpoint, TreeItem):
			for c in startpoint.children:
				self.SetFullNames(c,startpoint.fullname + '/')

	def GetNodeByName(self, name):
		if name[0] == '/':
			# use fully qualified name
			return self.NodesByFullName[name]
		else:
			# use short name
			return self.NodesByName[name]

	def NodeExists(self, name):
		if name[0] == '/':
			return name in self.NodesByFullName
		else:
			return name in self.NodesByName

	def SceneExists(self, name):
		if name[0] != '/':
			return name in self.ScenesByName
		else:
			for n, s in self.ScenesByName.iteritems():
				if name == s.fullname:
					return True
			return False

	def GetSceneByName(self,name):
		if name[0] != '/':
			return self.ScenesByName[name]
		else:
			for n, s in self.ScenesByName.iteritems():
				if name == s.fullname:
					return s
			return None

	def PrintTree(self, startpoint, indent, msg):
		if msg is not None:
			debug.debugPrint('ISY', 'Graph for ', msg)
		if isinstance(startpoint, Scene):
			debug.debugPrint('ISY', indent + startpoint.__repr__())
			for m in startpoint.members:
				if m[0] == 16:
					sR = 'R'
				elif m[0] == 32:
					sR = 'C'
				else:
					sR = 'X'
				debug.debugPrint('ISY', indent + "-" + sR + "--" + (m[1].__repr__()))
		elif isinstance(startpoint, TreeItem):
			debug.debugPrint('ISY', indent + startpoint.__repr__())
			for c in startpoint.children:
				self.PrintTree(c, indent + "....", None)
		else:
			debug.debugPrint('ISY', "Funny thing in tree ", startpoint.__repr__)
