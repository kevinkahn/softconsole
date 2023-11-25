import datetime
import os
import requests
import shutil
import subprocess
import time

"""
NOTE: This gets used in initial setup of console by the setup program
** Don't add any dependencies on other parts of the console (E.g., no logging
"""


def StageVersion(vdir, tag, label, uselog=False):
	if uselog:
		logf = open('stagelog.log', 'a')
	else:
		logf = open('stagelog.log', 'w')
	print(datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"), file=logf)
	print("Staging " + tag + " in " + vdir + ' because ' + label, file=logf)

	cwd = os.getcwd()
	try:
		os.chdir(vdir)
	except Exception as E:
		print("Staging directory {} doesn't exist - try to create it ({})".format(vdir, E))
		os.mkdir(vdir)
		os.chdir(vdir)
	shutil.rmtree('stagedversion', True)
	os.mkdir('stagedversion')
	os.chdir('stagedversion')
	if tag == '*live*':
		subprocess.call('wget https://github.com/kevinkahn/softconsole/tarball/master', shell=True, stdout=logf, stderr=logf)
		subprocess.call('tar -zxls --strip-components=1 < master', shell=True, stdout=logf, stderr=logf)
		subprocess.call('chown -R pi: *', shell=True, stdout=logf, stderr=logf)
		os.remove('master')
	else:
		subprocess.call('wget https://github.com/kevinkahn/softconsole/archive/' + tag + '.tar.gz', shell=True, stdout=logf, stderr=logf)
		subprocess.call('tar -zxls --strip-components=1 < ' + tag + '.tar.gz', shell=True, stdout=logf, stderr=logf)
		sha, cdate = GetSHA(tag)
		with open('versioninfo', 'w') as f:
			f.writelines(['{0}\n'.format(tag), '{0}\n'.format(sha), label + ': ' + time.strftime('%m-%d-%y %H:%M:%S\n'),
						  'Commit of: {0}\n'.format(cdate)])
		os.remove(tag + '.tar.gz')
	# noinspection PyBroadException
	try:
		os.chmod('runconsole.py', 0o555)
	except:
		pass
	# noinspection PyBroadException
	try:
		os.chmod('console.py', 0o555)
	except:
		pass

	os.chdir(cwd)
	logf.close()

# noinspection PyBroadException
def InstallStagedVersion(d, Bookworm=False):
	logf = open('stagelog.log', 'a')
	print("Installing in {}".format(d), file=logf)
	shutil.rmtree(d + '/previousversion', True)  # don't keep multiple previous version in tree
	os.rename(d, d + '.TMP')  # move active directory to temp
	os.rename(d + '.TMP/stagedversion', d)  # move new version into place
	os.rename(d + '.TMP', d + '/previousversion')  # save previous version
	os.chdir(d)

	if os.path.exists('../homesystem'):
		# noinspection PyBroadException
		try:
			subprocess.call('cp -u -r -p "example_configs"/* ../Console', shell=True, stdout=logf, stderr=logf)
		except:
			print('Copy of example_configs failed on homesystem', file=logf)

	if not os.path.exists('../Console/termshortenlist'):
		try:
			os.rename('example_configs/termshortenlist', '../Console/termshortenlist')
			print("Initialized termshortenlist", file=logf)
		except:
			print("Couldn't move termshortenlist in " + str(os.getcwd()), file=logf)

	if Bookworm and os.path.exists('scripts/softconsoleBW.service'):
		print('Use softconsoleBW.service for systemctl')
		shutil.copy('scripts/softconsoleBW.service', 'scripts/softconsole.service')

	print('Process upgrade extras script', file=logf)
	subprocess.call('bash ./scripts/upgradeprep.sh', shell=True, stdout=logf, stderr=logf)
	print('End upgrade extras script', file=logf)

	print('Setup systemd service from {}'.format(d), file=logf)
	os.chmod('runconsole.py', 0o555)
	os.chmod('console.py', 0o555)

	print('DO cp -f ' + 'scripts/softconsole.service /usr/lib/systemd/system', file=logf)
	suc = subprocess.call('sudo cp -f scripts/softconsole.service /usr/lib/systemd/system', shell=True)
	print('Service copy result: []', format(suc), file=logf)
	suc = subprocess.call('sudo systemctl daemon-reload', shell=True)
	print('Reload result: {}'.format(suc), file=logf)

	if not os.path.exists('/home/pi/bin'):
		os.mkdir('/home/pi/bin')
	shutil.copytree('scripts/tools', '/home/pi/bin')
	if os.path.exists('/home/pi/bin/authorized_keys'):
		shutil.copy('/home/pi/bin/authorized_keys', '/home/pi/.ssh')
	subprocess.call('chmod +x /home/pi/bin/*', shell=True, stdout=logf, stderr=logf)

	logf.close()
	os.chdir('..')


def GetSHA(tag):
	r = requests.get('https://api.github.com/repos/kevinkahn/softconsole/tags')
	d = r.json()
	sha = 'not found'
	url = 'none'
	for i in d:
		if i['name'] == tag:
			sha = i['commit']['sha']
			url = i['commit']['url']
			break
	if sha == 'not found':
		return 'no current sha', 'no release info'
	r = requests.get(url)
	d = r.json()
	c = d['commit']['committer']['date']
	return sha, c
