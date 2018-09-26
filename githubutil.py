import os, shutil, subprocess, requests, time

"""
NOTE: This gets used in initial setup of console by the setup program
** Don't add any dependencies on other parts of the console (E.g., no logging
"""

def StageVersion(vdir, tag, label):
	print("Staging " + tag + " in " + vdir + ' because ' + label)
	cwd = os.getcwd()
	os.chdir(vdir)
	shutil.rmtree('stagedversion', True)
	os.mkdir('stagedversion')
	os.chdir('stagedversion')
	if tag == '*live*':
		subprocess.call('wget https://github.com/kevinkahn/softconsole/tarball/master', shell=True)
		subprocess.call('tar -zxls --strip-components=1 < master', shell=True)
		subprocess.call('chown -R pi: *', shell=True)
		os.remove('master')
	else:
		subprocess.call('wget https://github.com/kevinkahn/softconsole/archive/' + tag + '.tar.gz', shell=True)
		subprocess.call('tar -zxls --strip-components=1 < ' + tag + '.tar.gz', shell=True)
		sha, cdate = GetSHA(tag)
		with open('versioninfo', 'w') as f:
			f.writelines(['{0}\n'.format(tag), '{0}\n'.format(sha), label + ': ' + time.strftime('%m-%d-%y %H:%M:%S\n'),
						  'Commit date: {0}\n'.format(cdate)])
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


def InstallStagedVersion(d):
	shutil.rmtree(d + '/previousversion', True)  # don't keep multiple previous version in tree
	os.rename(d, d + '.TMP')  # move active directory to temp
	os.rename(d + '.TMP/stagedversion', d)  # move new version into place
	os.rename(d + '.TMP', d + '/previousversion')  # save previous version
	os.chdir(d)
	try:
		os.remove(d + '/../Console/termshortenlist')
	except:
		pass
	os.rename(d + '/scripts/termshortenlist', d + '../Console/termshortenlist')
	print('Process upgrade extras script')
	subprocess.call('sudo bash ' + './scripts/upgradeprep.sh', shell=True)
	print('End upgrade extras script')
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
		return 'no current sha','no release info'
	r = requests.get(url)
	d = r.json()
	c = d['commit']['committer']['date']
	return sha, c
