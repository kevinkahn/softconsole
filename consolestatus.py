import collections
from itertools import zip_longest

nodes = collections.OrderedDict()
noderecord = collections.namedtuple('noderecord', ['status', 'uptime', 'error', 'rpttime', 'FirstUnseenErrorTime',
												   'GlobalLogViewTime', 'registered', 'versionname', 'versionsha',
												   'versiondnld', 'versioncommit', 'boottime', 'osversion', 'hw',
												   'APIXUfetches', 'queuetimemax24', 'queuetimemax24time',
												   'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
												   'queuetimemaxtime', 'daystartloops', 'queuedepthmax', 'queuetimemax',
												   'APIXUfetches24', 'queuedepthmaxtime'])

defaults = {k: v for (k, v) in zip_longest(noderecord._fields, (
	'unknown', 0, -2, 0, 0, 0, 0), fillvalue='unknown*')}


def NewNode(nd):
	print('New node: {}'.format(nd))
	nodes[nd] = noderecord(**defaults)


def UpdateStatus(nd, stat):
	if nd not in nodes: NewNode(nd)
	print('Update {}: {}'.format(nd, stat))
	nodes[nd] = nodes[nd]._replace(**stat)
	print('Nodeinfo: {}'.format(nodes))
