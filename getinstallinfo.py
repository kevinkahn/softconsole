import sys, time, os, wget, shutil, subprocess
from functools import partial as p

gitselector = {'stable': 'currentrelease', 'personal': 'homerelease', 'beta': 'currentbeta'}
gitprefix = 'https://raw.githubusercontent.com/kevinkahn/softconsole/'
installscripts = {'vncserverpi.service': 'scripts/', 'lxterminal.conf': 'scripts/', 'githubutil.py': ''}
setgroupaccess = {'/sys/class/backlight/10-0045/brightness'}


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
	return ["echo Adafruit {} screen\n".format(scr),
			# below from https://learn.adafruit.com/adafruit-pitft-3-dot-5-touch-screen-for-raspberry-pi/easy-install-2
			# apt-get update done early in install script
			# apt-get install -y git python3-pip\n  done earlier
			"pip3 install --upgrade adafruit-python-shell click\n",
			"git clone https://github.com/adafruit/Raspberry-Pi-Installer-Scripts.git\n",
			"cd Raspberry-Pi-Installer-Scripts\n",
			"python ./adafruit-pitft.py --display={} --rotation={} --reboot=no --install-type=console \n".format(scr,
																												 rotation),
			'cd ..\n'
			'mv Raspberry-Pi-Installer-Scripts .consoleinstallleftovers\n']


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

print("**************************************************************", flush=True)
print("**************************************************************", flush=True)
print(" Will now collect all necessary configuration information", flush=True)
print(" After this the install can run unattended to completion", flush=True)
print("**************************************************************", flush=True)
print("**************************************************************", flush=True)
time.sleep(3)
Buster = False
with open('/etc/issue') as f:
	sysver = f.readline()
	if "Linux 10" in sysver:
		Buster = True
	if "Linux 12" in sysver:
		Bookworm = True
		print("**************************************************************", flush=True)
		print("**************************************************************", flush=True)
		print("Installing for Bookworm", flush=True)
		print("**************************************************************", flush=True)
		print("**************************************************************", flush=True)

print("**************************************************************", flush=True)
print("   Set group access on needed hardware", flush=True)
for item in setgroupaccess:
	print(item)
	suc = subprocess.call('sudo chmod g+w {}', format(item), shell=True)
	print('  Result: {}'.format(suc))
print("**************************************************************", flush=True)
AddToScript('Buster', 'Y' if Buster else 'N')
AddToScript('Bookworm', 'Y' if Bookworm else 'N')
if piinstall:
	NodeName = GetVal("Enter name for system or return to leave as is:")
	AddToScript('NodeName', NodeName)

personal = GetYN("Is this the developer personal system (Y/N) (bit risky to say Y if it not)?")
if personal:
	with open('homesystem', 'w') as f:
		f.write('homesystem\n')
AddToScript('Personal', personal)

selectbeta = False
beta = GetYN("Download current beta as well as stable? (usually waste of time)")
if beta:
	selectbeta = GetYN("Set beta as version to run?")

# AddToScript('InstallBeta', beta)
AddToScript('AutoConsole', GetYN("Autostart console (Y/N)?"))
AddToScript('Reboot', GetYN("Automatically reboot to clean system after install?"))

GetScripts('personal' if personal else 'stable')
if beta:
	GetScripts('beta', save=('personal' if personal else 'stable'))

screentype = '--'

# adafruit script rotations {'28r': 4, '28c': 2, '35r': 4}
screeninstallcode = {'28r': p(adafruit, '28r', 0), '28c': p(adafruit, '28c', 180), '35r': p(adafruit, '35r', 0),
					 'pi7': p(doflip, 'pi7'), '5incap': p(doflip, 'pi7'), '--': p(noscreen, '--')}

supportedscreens = list(screeninstallcode.keys())
supportedscreens.remove('--')

baseorientation = {'28c': 'power on left',
				   '28r': 'power on left',
				   '35r': 'power on left',
				   'pi7': 'power at bottom',
				   '5incap': 'power at top',
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
	if rot != 0:
		installsrc.append('echo Soft rotation code {}\n'.format(rot))

screentp = screentype + 'B' if Buster else screentype
screentp = screentype + 'BW' if Bookworm else screentype

with open('.Screentype', 'w') as f:
	if rot == 0:
		f.write(screentp + '\n')
	else:
		f.write(screentp + ',' + str(rot) + '\n')

with open('installvals', 'w') as f:
	f.writelines(scriptvars)
	if Bookworm:
		f.write("export BOOKWORM=True")
with open('installscreencode', 'w') as f:
	f.writelines(installsrc)

HubName = ""
ans = ""
IP = ""
ISYUSER = ""
ISYPWD = ""
HATOKEN = ""
exswitch = ""

if personal:
	MinExampHA = False
else:
	MinExampHA = GetYN("Set up minimal Home Assistant example system?")  # if not MinExampISY else False

HAexswitch = 'unknown'
if MinExampHA:
	go = False
	while not go:
		HubName = input("Name to use for the HA hub (defaults to HASS):")
		if HubName == "":
			HubName = "HASS"
		IP = input("full URL to access HA: ")
		if IP.endswith('/'):
			IP = IP[0:-1]
		HATOKEN = input("HA access token: ")
		HAexswitch = input("Example switch to use (HA entity name): ")
		print("HA Name: " + HubName)
		print("IP:       " + IP)
		print("PASSWORD: " + HATOKEN)
		print("SWITCH:   " + "[[" + HAexswitch + "]]")
		go = GetYN("OK? (y/n)")

print("Set up directory environment for console")

with open('versionselector', 'w') as f:
	f.write('stable\n')

dirs = ['Console', 'consolestable', 'consolebeta', 'consolerem', 'consoledev', 'Console', 'Console/cfglib',
		'Console/.HistoryBuffer']
if personal:
	dirs.append('consolecur')
for pdir in dirs:
	# noinspection PyBroadException
	try:
		os.mkdir(pdir)
		print("Created: " + str(pdir))
	except:
		print("Already present: " + str(pdir))
	shutil.chown(pdir, user='pi', group='pi')

if MinExampHA:
	with open('/home/pi/Console/cfglib/auth.cfg', "w") as f:
		cfg = ("[" + HubName + "]",
			   "type = HASS.1",
			   "address = " + IP,
			   "password = " + HATOKEN,
			   "\n")
		f.write("\n".join(cfg))
	with open('/home/pi/Console/config.txt', 'w') as f:
		cfg = ('cfglib = cfglib',
			   'include = auth.cfg, myclock.cfg',
			   'DefaultHub = ' + HubName,
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
			   '[[' + HAexswitch + ']]',
			   "\n")
		f.write("\n".join(cfg))

print("\n\nSoftconsole install paramters:")
for l in scriptvars:
	print('    ' + l.replace('\n', ''))

if MinExampHA:
	print("    Create minimal example Home Assistant configuration")
else:
	print("    Skip minimal example configuration")
print('---------------------', flush=True)

import githubutil as U

print('Download console code - this takes a while', flush=True)

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
	if selectbeta:
		with open('versionselector', 'w') as f:
			f.write('beta\n')
authdir = '/boot/auth' if os.path.exists('/boot/auth') else '/boot/firmware/auth' if os.path.exists(
	'/boot/firmware/auth') else None
print("****************************************************************", flush=True)
print(" auth directory found at {}".format(authdir))
print("****************************************************************", flush=True)
if authdir is not None:
	shutil.rmtree('Console/local', ignore_errors=True)
	shutil.copytree(authdir, 'Console/local')
	# shutil.move(authdir, 'Console/local')
	if os.path.exists('Console/local/fstabadj.txt'):
		shutil.copy('/etc/fstab', 'fstab.orig')
		with open('Console/local/fstabadj.txt', 'r') as adds:
			with open('fstab.orig', 'a') as f:
				shutil.copyfileobj(adds, f)
		subprocess.call('sudo cp -f fstab.orig /etc/fstab', shell=True)

shutil.copytree('/home/pi/consolestable/example_configs', '/home/pi/Console', dirs_exist_ok=True)
#subprocess.call("cp -r /home/pi/consolestable/'example_configs'/* /home/pi/Console", shell=True)
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
