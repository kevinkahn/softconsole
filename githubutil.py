import os, shutil, subprocess, requests, time, datetime

"""
NOTE: This gets used in initial setup of console by the setup program
** Don't add any dependencies on other parts of the console (E.g., no logging
"""

def StageVersion(vdir, tag, label):
	print(datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"), file=open("stagelog.log", "a"))
	print("Staging " + tag + " in " + vdir + ' because ' + label, file=open("stagelog.log", "a"))
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


# noinspection PyBroadException
def InstallStagedVersion(d):
	shutil.rmtree(d + '/previousversion', True)  # don't keep multiple previous version in tree
	os.rename(d, d + '.TMP')  # move active directory to temp
	os.rename(d + '.TMP/stagedversion', d)  # move new version into place
	os.rename(d + '.TMP', d + '/previousversion')  # save previous version
	os.chdir(d)

	if os.path.exists('../homesystem'):
		# noinspection PyBroadException
		try:
			subprocess.call('cp -r -u --backup=numbered "example configs"/* ../Console', shell=True)
		# os.remove('../Console/termshortenlist')
		# print('Removed existing shortenlist from homesystem', file=open("stagelog.log", "a"))
		except:
			print('Copy of example configs failed on homesystem', file=open("stagelog.log", "a"))

	if not os.path.exists('../Console/termshortenlist'):
		try:
			os.rename('example configs/termshortenlist', '../Console/termshortenlist')
			print("Initialized termshortenlist", file=open("stagelog.log", "a"))
		except:
			print("Couldn't move termshortenlist in " + str(os.getcwd()), file=open("stagelog.log", "a"))

	print('Process upgrade extras script', file=open("stagelog.log", "a"))
	subprocess.call('sudo bash ' + './scripts/upgradeprep.sh', shell=True)
	print('End upgrade extras script', file=open("stagelog.log", "a"))
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
