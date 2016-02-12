import xmltodict
import config
from config import ISYdebug
from logsupport import Info, Warning, Error


def get_real_time_status(addrlist):
    # multiple calls here is substantially faster than one call for all status then selecting devices
    # this proc assumes a device that returns a simple ST value for status
    statusdict = {}
    for addr in addrlist:
        r = config.ISYrequestsession.get('http://' + config.ISYaddr + '/rest/status/' + addr, verify=False)
        statusdict[addr] = int(xmltodict.parse(r.text)['properties']['property']['@value'])
    return statusdict


class TreeItem:
    def __init__(self, name, addr, parentaddr):
        self.name = name
        self.address = addr
        self.parent = parentaddr  # replaced by actual obj reference at end of tree build
        self.children = []

    def __repr__(self):
        return 'Tree Iten: ' + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children'


class OnOffItem:
    def SendCommand(self, state, fast):
        selcmd = (('DOF', 'DFOF'), ('DON', 'DFON'))
        config.debugprint(ISYdebug, "OnOff sent: ", selcmd[state][fast], ' to ', self.name)
        url = 'http://' + config.ISYaddr + '/rest/nodes/' + self.address + '/cmd/' + selcmd[state][fast]
        r = config.ISYrequestsession.get(url)
        return r


class Folder(TreeItem):
    def __init__(self, flag, name, addr, parenttyp, parentaddr):
        TreeItem.__init__(self, name, addr, parentaddr)
        self.flag = flag
        self.parenttype = parenttyp

    def __repr__(self):
        return "Folder: " + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children: '


class Node(Folder, OnOffItem):
    def __init__(self, flag, name, addr, parenttyp, parentaddr):
        Folder.__init__(self, flag, name, addr, parenttyp, parentaddr)
        self.pnode = None  # for things like KPLs
        # no use for nodetype now
        # enabled?]
        # device class -energy management
        # wattage, dcPeriod, status dict (property - so a list of statuses

    def __repr__(self):
        return "Node: " + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children: '


class Scene(TreeItem, OnOffItem):
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

    def __repr__(self):
        return "Scene: " + self.name + '/' + self.address + ' ' + str(
            len(self.members)) + ' members: ' + self.members.__repr__()


class ProgramFolder(TreeItem):
    def __init__(self, nm, itemid, pid):
        TreeItem.__init__(self, nm, itemid, pid)
        self.status = False
        # not using lastRunTime, lastFinishTime

    def __repr__(self):
        return 'ProgFolder' + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children'


class Program(ProgramFolder):
    def __init__(self, nm, itemid, pid):
        ProgramFolder.__init__(self, nm, itemid, pid)
        # not using enabled, runAtStartup,running

    def runThen(self):
        config.debugprint(ISYdebug, "runThen sent to ", self.name)
        url = config.ISYprefix + 'programs/' + self.address + '/runThen'
        r = config.ISYrequestsession.get(url)
        return r

    def __repr__(self):
        return 'Program' + self.name + '/' + self.address + ' ' + str(len(self.children)) + ' children'


class ISY:
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
                config.Logs.Log("Missing parent: " + node.name, Error)
            if node.parent <> node:  # avoid root
                node.parent.children.append(node)

    def __init__(self, ISYsession, ISYaddr):
        """
        Get and parse the ISY configuration to set up an internal analog of its structure
        :param ISYsession:
        :param ISYaddr:
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
            n = Node(node['@flag'], node['name'], node['address'], int(node['parent']['@type']),
                     node['parent']['#text'])
            fixlist.append((n, node['pnode']))
            self.NodesByAddr[n.address] = n
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
                print 'Scene with no members', scene['name']
        self.LinkChildrenParents(self.ScenesByAddr, self.ScenesByName, self.FoldersByAddr, self.NodesByAddr)
        if ISYdebug:
            self.PrintTree(self.NodeRoot, "    ")

        """
        Build the Program tree
        """

        r = ISYsession.get('http://' + ISYaddr + '/rest/programs?subfolders=true', verify=False)
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
