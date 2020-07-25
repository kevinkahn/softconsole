import sys


def GetYN(prompt, Allownum=False):
	while True:
		ans = input(prompt + ' ')
		if ans in ('Y', 'y'):
			return True
		elif ans in ('N', 'n'):
			return False
		elif Allownum:
			return ans
		else:
			print('Answer Y or N')


def GetVal(prompt, allowed=None):
	while True:
		ans = input(prompt + ' ')
		if allowed is None:
			return ans
		else:
			if ans in allowed:
				return ans
			else:
				print('Choices are {}'.format(allowed))


scriptvars = []


def AddToScript(varset, value):
	global scriptvars
	if isinstance(value, bool):
		set = ('N', 'Y')[value]
	elif isinstance(value, str):
		set = value
	else:
		set = str(value)
	scriptvars.append(varset + '=' + set + '\n')


AddToScript('NodeName', GetVal("What name for this system?"))
AddToScript('VNCstdPort', GetYN("Install VNC on standard port (Y/N/alt port number)?", Allownum=True))
AddToScript('Personal', GetYN("Is this the developer personal system (Y/N) (bit risky to say Y if it not)?"))
AddToScript('InstallBeta', GetYN("Download current beta as well as stable? (usually waste of time)"))
AddToScript('AutoConsole', GetYN("Autostart console (Y/N)?"))
AddToScript('Reboot', GetYN("Automatically reboot to continue install after system setup?"))

flip7 = False
screentype = '--'
supportedscreens = ('28r', '28c', '35r', 'pi7')
rotationcodes = {'28r': 4, '28c': 2, '35r': 4}

doscreen = GetYN("Do you want to install a known screen (Alternative is to install any screen drivers yourself)?")
if doscreen:
	screentype = GetVal("What type screen ({})?".format(supportedscreens), supportedscreens)
	if screentype == 'pi7':
		flip7 = GetYN("Flip 7 inch screen so power at top? (Y/N)")
AddToScript('Flip7', flip7)
AddToScript('ScreenType', screentype)

fin = open('/home/pi/adafruit-pitft.sh')
displays = []
while not displays:
	l = fin.readline()
	if l.startswith('PITFT_TYPES='):
		displays = l[l.index('(') + 1: l.index(')')].replace('"', '').split(' ')
	else:
		pass
fin.close()

try:
	dnum = displays.index(screentype) + 1
except:
	print('Screen name not found in Adafruit scripts - report to developer!')
	sys.exit(1)

fout = open('installvals', 'w')
fout.writelines(scriptvars)
fout.close()
if screentype in rotationcodes:
	fout = open('adafinput', 'w')
	fout.write(str(dnum) + '\n')
	fout.write(str(rotationcodes[screentype]) + '\n')
	fout.write('Y\n')  # pi console to pitft
	fout.write('N\n')  # don't reboot
	fout.close()

ISYname = ""
ans = ""
ISYIP = ""
ISYUSER = ""
ISYPWD = ""
exswitch = ""
MinExamp = GetYN("Set up minimal example system?")

if MinExamp:
	go = False
	while not go:
		ISYname = input("Name to use for the ISY hub (defaults to ISY): ")
		if ISYname == "":
			ISYname = "ISY"
		ISYIP = input("full URL to access ISY: ")
		if ISYIP.endswith('/'):
			ISYIP = ISYIP[0:-1]
		ISYUSER = input("ISY user name: ")
		ISYPWD = input("ISY password: ")
		exswitch = input("Example switch to use (ISY name): ")
		print("ISY Name: " + ISYname)
		print("IP:       " + ISYIP)
		print("USER:     " + ISYUSER)
		print("PASSWORD: " + ISYPWD)
		print("SWITCH:   " + "[[" + exswitch + "]]")
		go = GetYN("OK? (y/n)")
	with open('/home/pi/Consoleauth', "w") as f:
		cfg = ("[" + ISYname + "]",
			   "type = ISY",
			   "address = " + ISYIP,
			   "user = " + ISYUSER,
			   "password = " + ISYPWD,
			   "\n")
		f.write("\n".join(cfg))
	with open('/home/pi/ConsoleMinEx', 'w') as f:
		cfg = ('cfglib = cfglib',
			   'include = auth.cfg, myclock.cfg',
			   'DefaultHub = ' + ISYname,
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

print("\n\nSoftconsole install paramters:")
for l in scriptvars:
	print('    ' + l.replace('\n', ''))
if MinExamp:
	print("    Create minimal example configuration")
else:
	print("    Skip minimal example configuration")
