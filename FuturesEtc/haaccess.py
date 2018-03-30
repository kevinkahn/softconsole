from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from requests import get
import json
import pprint

url = 'http://rpi-dev7.pgawhome:8123/api/states'



response = get(url)
#print(response.text)
states = {}
eids = {}
js = json.loads(response.text)
print(js)
#print pprint.pprint(js)
print('===========================')
for item in js:

	fn = item['attributes'].pop('friendly_name',"NO FRIENDLY NAME")
	eid = item['entity_id']
	if not fn in states:
		states[fn] = [(eid,item['attributes'])]
	else:
		states[fn].append((eid,item['attributes']))
	if not eid in eids:
		eids[eid] = []
	eids[eid].append(str(fn))

for e, v in eids.iteritems():
	print(e)
	for f in v:
		print("    ", f)
print("====================================")
for s, v in states.iteritems():
	print(s)
	for i in v:
		print("    ", i)

#	print '++++++++++++++++++++++++++'
	#print "**",item
#	for key, val in item.iteritems():
#		print '*******',key
#		print '**************',val
#		print '---------------------------'
