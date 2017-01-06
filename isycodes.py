import config

EVENT_CTRL = {
	"_0": "Heartbeat",
	"_1": "Trigger",
	"_2": "Protocol Specific",
	"_3": "Nodes Updated",
	"_4": "System Config Updated",
	"_5": "System Status",
	"_6": "Internet Access",
	"_7": "System Progress",
	"_8": "Security System",
	"_9": "System Alert",
	"_10": "Electricity",
	"_11": "Climate",
	"_12": "AMI/SEP",
	"_13": "Ext Energy Mon",
	"_14": "UPB Linker",
	"_15": "UPB Dev State",
	"_16": "UPB Dev Status",
	"_17": "Gas",
	"_18": "ZigBee",
	"_19": "Elk",
	"_20": "Device Link",
	"_21": "Z-Wave",
	"_22": "Billing",
	"_23": "Portal",
	"DON": "Device On",
	"DFON": "Device Fast On",
	"DOF": "Device Off",
	"DFOF": "Device Fast Off",
	"ST": "Status",
	"OL": "On Level",
	"RR": "Ramp Rate",
	"BMAN": "Start Manual Change",
	"SMAN": "Stop Manual Change",
	"CLISP": "Setpoint",
	"CLISPH": "Heat Setpoint",
	"CLISPC": "Cool Setpoint",
	"CLIFS": "Fan State",
	"CLIMD": "Thermostat Mode",
	"CLIHUM": "Humidity",
	"CLIHCS": "Heat/Cool State",
	"UOM": "Thermostaat Units",
	"BRT": "Brighten",
	"DIM": "Dim",
	"X10": "Direct X10 Commands",
	"BEEP": "Beep"
}


def formatwsitem(sid, seq, code, action, node, info, extra):
	paddr = 'zzzzz'
	try:
		if action is None:
			action = 'NONE'
		if node is None:
			node = 'NONE'
		if info is None:
			info = 'NONE'
		try:
			isynd = config.ISY.NodesByAddr[node].name
		except:
			isynd = node
		pretty = ' ' + sid + '/' + str(seq) + ' '
		EC = EVENT_CTRL[code]
		if EC == 'Status':
			return pretty + 'Status ' + isynd + ': ' + str(action)
		elif EC == 'Heartbeat':
			return pretty + 'Heartbeat: ' + str(action)
		elif EC == 'Ramp Rate':
			return pretty + 'Ramp ' + isynd + ': ' + str(action)
		elif EC == 'Trigger' and str(action) == '0':
			runinfo = ''
			if 'r' in info:
				runinfo = runinfo + ' Last run ' + info['r']
			if 'f' in info:
				runinfo = runinfo + ' Last finish ' + info['f']
			if 'nsr' in info:
				runinfo = runinfo + ' Next run ' + info['nsr']
			other = ''
			if 'off' in info:
				other = 'Disabled '
			if 'rr' in info:
				other = other + 'Run@reboot'
			if 's' in info:
				stat = ' Status: ' + info['s']
			else:
				stat = ''
			paddr = str("0x%0.4X"%int(info['id'], 16))[2:]
			return pretty + 'ProgRun ' + config.ISY.ProgramsByAddr[paddr].name + runinfo + stat + other
		elif EC == "System Status":
			return pretty + "System Status " + ('Not Busy', 'Busy', 'Idle', 'Safe Mode')[int(action)]
		else:
			pretty = pretty + EC + ': ' + str(action) + ' Node: ' + isynd + ' ' + str(info)
		if extra:
			pretty = pretty + 'Extra: ' + repr(extra)
	except:
		pretty = 'FORMATTING ERROR: ' + repr(sid) + repr(seq) + repr(code) + repr(action) + repr(node) + repr(
			info) + repr(extra)
	return pretty
