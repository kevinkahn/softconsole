import sys, time, os, wget, stat, shutil, subprocess
from functools import partial as p

neededfiles = {'adafruit-pitft-touch-cal': 'https://raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/',
			   'adafruit-pitft.sh': 'https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/'}

gitselector = {'stable': 'currentrelease', 'personal': 'homerelease', 'beta': 'currentbeta'}
gitprefix = 'https://raw.githubusercontent.com/kevinkahn/softconsole/'
installscripts = {'vncserverpi.service': 'scripts/', 'lxterminal.conf': 'scripts/', 'githubutil.py': ''}


def GetScripts(vers, save=''):
	if save != '':
		for s in installscripts:
			os.rename(s, '.consoleinstallleftovers/' + s + '.' + save)
	for nm, floc in installscripts.items():
		wget.download(gitprefix + gitselector[vers] + '/' + floc + nm, nm, bar=None)
	shutil.chown('lxterminal.conf', user='pi', group='pi')


def GetYN(prompt, Allownum=False):
	while True:
		answer = input(prompt + ' ')
		if answer in ('Y', 'y'):
			return True
		elif answer in ('N', 'n'):
			return False
		elif Allownum:
			return answer
		else:
			print('Answer Y or N')


def GetVal(prompt, allowed=None):
	while True:
		answer = input(prompt + ' ')
		if allowed is None:
			return answer
		else:
			if answer in allowed:
				return answer
			else:
				print('Choices are {}'.format(allowed))


# noinspection PyBroadException
def GetInt(prompt, allowed=None):
	while True:
		try:
			answer = int(input(prompt + ' '))
			if allowed is None:
				return answer
			else:
				if answer in allowed:
					return answer
				else:
					print('Choices are {}'.format(allowed))
		except:
			print('Bad input - choices are: {}'.format(allowed))


scriptvars = []


def AddToScript(varset, value):
	global scriptvars
	if isinstance(value, bool):
		setting = ('N', 'Y')[value]
	elif isinstance(value, str):
		setting = value
	else:
		setting = str(value)
	scriptvars.append(varset + '=' + setting + '\n')


def adafruit(scr, rotation):
	fin = open('/home/pi/adafruit-pitft.sh')
	displays = []
	while not displays:
		line = fin.readline()
		if line.startswith('PITFT_TYPES='):
			displays = line[line.index('(') + 1: line.index(')')].replace('"', '').split(' ')
		else:
			pass
	fin.close()

	# noinspection PyBroadException
	try:
		dnum = displays.index(scr) + 1
	except:
		print('Screen name not found in Adafruit scripts - report to developer!')
		sys.exit(1)
	fout = open('adafinput', 'w')
	fout.write(str(dnum) + '\n')
	fout.write(str(rotation) + '\n')
	fout.write('Y\n')  # pi console to pitft
	fout.write('N\n')  # don't reboot
	fout.close()
	return ["echo Adafruit {} screen\n".format(scr),
			"./adafruit-pitft.sh < adafinput\n",
			"raspi-config nonint do_boot_behaviour B4 # set boot to desktop already logged in\n"]


# noinspection PyUnusedLocal
def doflip(scr):
	global baseorientation
	print("If you are not using a Pi4 you can use hardware to flip the base orientation")
	print("of the display so that the power connector is on the top.")
	print("If you are on a Pi4 use the soft rotation option that will get asked for next")
	print("Also use the soft rotation option for other orientations.")
	flip = GetYN("Flip 7 inch screen so power at top using hardware option? (Y/N)")
	if flip:
		baseorientation['pi7'] = 'power at top'
		return ['echo Flip 7 inch screen\n', 'echo "lcd_rotate=2" >> /boot/config.txt\n']
	else:
		return ['echo Nornmal 7 inch screen\n', ]


def noscreen(scr):
	return ['echo User setup screen with type: {}\n'.format(scr), ]


# Start of script
piinstall = len(sys.argv) == 1

shutil.rmtree('.consoleinstallleftovers', ignore_errors=True)
os.mkdir('.consoleinstallleftovers')

if piinstall:
	for n, loc in neededfiles.items():
		# noinspection PyBroadException
		try:
			os.remove(n)
		except Exception:
			pass
		wget.download(loc + n, n, bar=None)
		os.chmod(n, stat.S_IXUSR)

print("**************************************************************", flush=True)
print("**************************************************************", flush=True)
print(" Will now collect all necessary configuration information", flush=True)
print(" After this the install can run unattended to completion", flush=True)
print("**************************************************************", flush=True)
print("**************************************************************", flush=True)
time.sleep(3)
with open('/etc/issue') as f:
	sysver = f.readline()
	if "Linux 10" in sysver:
		Buster = True
AddToScript('Buster', 'Y' if Buster else 'N')
if piinstall:
	AddToScript('NodeName', GetVal("What name for this system?"))
	AddToScript('VNCstdPort', GetYN("Install VNC on standard port (Y/N/alt port number)?", Allownum=True))
personal = GetYN("Is this the developer personal system (Y/N) (bit risky to say Y if it not)?")
if personal:
	with open('homesystem', 'w') as f:
		f.write('homesystem\n')
AddToScript('Personal', personal)
beta = GetYN("Download current beta as well as stable? (usually waste of time)")
AddToScript('InstallBeta', beta)
AddToScript('AutoConsole', GetYN("Autostart console (Y/N)?"))
AddToScript('Reboot', GetYN("Automatically reboot to clean system after install?"))

GetScripts('personal' if personal else 'stable')
if beta: GetScripts('beta', save=('personal' if personal else 'stable'))

screentype = '--'
supportedscreens = ('28r', '28c', '35r', 'pi7')
# adafruit script rotations {'28r': 4, '28c': 2, '35r': 4}
screeninstallcode = {'28r': p(adafruit, '28r', 4), '28c': p(adafruit, '28c', 2), '35r': p(adafruit, '35r', 4),
					 'pi7': p(doflip, 'pi7'), '--': p(noscreen, '--')}
baseorientation = {'28c': 'power on left',
				   '35r': 'power on left',
				   'pi7': 'power at bottom',
				   '--': 'is unknown'}

if piinstall:
	doscreen = GetYN("Do you want to install a known screen (Alternative is to install any screen drivers yourself)?")
	if doscreen:
		screentype = GetVal("What type screen ({})?".format(supportedscreens), supportedscreens)
		installsrc = screeninstallcode[screentype]()
	else:
		screentype = GetVal("Enter name of screen for console reference:")
		installsrc = screeninstallcode['--']()
else:
	installsrc = []
	if GetYN('Are you using a standard screen? ({})'.format(supportedscreens)):
		screentype = GetVal('What type screen are you using ({})?'.format(supportedscreens), supportedscreens)
	else:
		screentype = GetVal("Enter name of screen for console reference:")

rot = 0
if screentype in baseorientation:
	print(" You can choose to rotate the display from its base orientation")
	print(" Base orientation for {} screen is with {}".format(screentype, baseorientation[screentype]))
	print(" Rotation options(power connection for reference:")
	print("     0: use base orientation")
	print("     1: 90 degrees counterclockwise")
	print("     2: 180 degrees counterclockwise (vertical flip)")
	print("     3: 270 degrees counterclockwise")
	rot = GetInt('Rotation option:', (0, 1, 2, 3, 4))
	if rot != 0: installsrc.append('echo Soft rotation code {}\n'.format(rot))

screentp = screentype + 'B' if Buster else screentype

with open('.Screentype', 'w') as f:
	if rot == 0:
		f.write(screentp + '\n')
	else:
		f.write(screentp + ',' + str(rot) + '\n')

with open('installvals', 'w') as f:
	f.writelines(scriptvars)
with open('installscreencode', 'w') as f:
	f.writelines(installsrc)

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

print("Set up directory environment for console")

with open('versionselector', 'w') as f:
	f.write('stable\n')

dirs = ['Console', 'consolestable', 'consolebeta', 'consolerem', 'consoledev', 'Console', 'Console/cfglib']
if personal: dirs.append('consolecur')
for pdir in dirs:
	# noinspection PyBroadException
	try:
		os.mkdir(pdir)
		print("Created: " + str(pdir))
	except:
		print("Already present: " + str(pdir))
	shutil.chown(pdir, user='pi', group='pi')

if MinExamp:
	with open('/home/pi/Console/cfglib/auth.cfg', "w") as f:
		cfg = ("[" + ISYname + "]",
			   "type = ISY",
			   "address = " + ISYIP,
			   "user = " + ISYUSER,
			   "password = " + ISYPWD,
			   "\n")
		f.write("\n".join(cfg))
	with open('/home/pi/Console/config.txt', 'w') as f:
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
print('---------------------', flush=True)

import githubutil as U

print('Download console code', flush=True)

if personal:
	# personal system
	U.StageVersion('consolestable', 'homerelease', 'Initial Install')
	print("Stage homerelease as stable")
else:
	U.StageVersion('consolestable', 'currentrelease', 'Initial Install')
	print("Stage standard stable release")

U.InstallStagedVersion('consolestable')
print('Installed stable version', flush=True)

if beta:
	U.StageVersion('consolebeta', 'currentbeta', 'Initial Install')
	print('Stage beta also')
	U.InstallStagedVersion('consolebeta')
	print('Intalled staged beta')

if os.path.exists('/boot/auth'):
	shutil.rmtree('Console/local', ignore_errors=True)
	shutil.move('/boot/auth', 'Console/local')

subprocess.call("cp -r /home/pi/consolestable/'example configs'/* /home/pi/Console", shell=True)
if piinstall:
	print("****************************************************************", flush=True)
	print("****************************************************************", flush=True)
	print(" System will now update/upgrade Raspbian", flush=True)
	print(" THIS COULD TAKE 10-15 MINUTES DEPENDING ON OUTSTANDING UPDATES", flush=True)
	print(" AND THE SPEED OF YOUR SD CARD!", flush=True)
	print(" After that it will install the softconsole using your input", flush=True)
	print("****************************************************************", flush=True)
	print("****************************************************************", flush=True)

	if screentype == '28c':
		print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
		print(" NOTE!!! NOTE!!! NOTE!!!")
		print(" If you are using the 28c screen, the settings from Adafruit that")
		print(" sets up are likely wrong.  Look at /boot/config.txt")
		print(" Next to last line should be: dtoverlay=pitft28-capacitive,rotate=180")
		print(" It may well show as rotate=90 after install due to bugs in their scripts")
		print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
		time.sleep(10)
time.sleep(3)
