import os, shutil, subprocess, requests, time


def StageVersion(dir, tag, label):
	print "Staging ", tag, " in ", dir, ' because ', label,
	sha = "zzz"
	cwd = os.getcwd()
	os.chdir(dir)
	shutil.rmtree('stagedversion', True)
	os.mkdir('stagedversion')
	os.chdir('stagedversion')
	subprocess.call('wget https://github.com/kevinkahn/softconsole/archive/' + tag + '.tar.gz', shell=True)
	subprocess.call('tar -zxls'
					' --strip-components=1 < ' + tag + '.tar.gz >> /home/pi/log.txt', shell=True)
	sha, cdate = GetSHA(tag)
	with open('versioninfo', 'w') as f:
		f.writelines(['{0}\n'.format(tag), '{0}\n'.format(sha), label + ': ' + time.strftime('%m-%d-%y %H:%M:%S\n'),
					  'Commit date: {0}\n'.format(cdate)])
	os.remove(tag + '.tar.gz')
	os.chdir(cwd)


def InstallStagedVersion(d):
	shutil.rmtree(d + '/previousversion', True)  # don't keep multiple previous version in tree
	os.rename(d, d + '.TMP')  # move active directory to temp
	os.rename(d + '.TMP/stagedversion', d)  # move new version into place
	os.rename(d + '.TMP', d + '/previousversion')  # save previous version
	print "Staged version installed in ", d


def GetSHA(tag):
	r = requests.get('https://api.github.com/repos/kevinkahn/softconsole/tags')
	d = r.json()
	for i in d:
		if i['name'] == tag:
			sha = i['commit']['sha']
			url = i['commit']['url']
			break
	r = requests.get(url)
	d = r.json()
	c = d['commit']['committer']['date']
	return (sha, c)
