from __future__ import print_function
from future.builtins.misc import input

ans = ""
ISYIP = ""
ISYUSER = ""
ISYPWD = ""
exswitch = ""
while not ans in ('y', 'Y', 'n', 'N'):
	ans = input("Set up minimal example system?")
if ans in ('y', 'Y'):
	go = ""
	while not go in ('y', 'Y'):
		ISYIP = input("full URL to access ISY: ")
		if ISYIP.endswith('/'):
			ISYIP = ISYIP[0:-1]
		ISYUSER = input("ISY user name: ")
		ISYPWD = input("ISY password: ")
		exswitch = input("Example switch to use (ISY name): ")
		print("IP:      " + ISYIP)
		print("USER:    " + ISYUSER)
		print("PASSWORD:" + ISYPWD)
		print("SWITCH:  " + "[[" + exswitch + "]]")
		go = input("OK? (y/n)")
	with open('/home/pi/Consoleauth', "w") as f:
		cfg = ("ISYaddr = " + ISYIP,
			   "ISYuser = " + ISYUSER,
			   "ISYpassword = " + ISYPWD,
			   "WunderKey = xxx",
			   "\n")
		f.write("\n".join(cfg))
	with open('/home/pi/ConsoleMinEx', 'w') as f:
		cfg = ('cfglib = cfglib',
			   'include = auth.cfg, myclock.cfg',
			   'HomeScreenName = test',
			   'PersistTO = 30',
			   'DimLevel = 5',
			   'DimTO = 15',
			   'DimIdleListNames = MyClock,',
			   'DimIdleListTimes = 20,',
			   'MainChain = test, MyClock',
			   '[test]',
			   'type = Keypad',
			   'label = My, Test',
			   '[[' + exswitch + ']]',
			   "\n")
		f.write("\n".join(cfg))
