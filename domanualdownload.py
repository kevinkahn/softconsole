import githubutil, os

exdir = os.getcwd()
print("Install from: {}".format(exdir))
try:
	with open('versioninfo') as f:
		versionname = f.readline()[:-1].rstrip()
		versionsha = f.readline()[:-1].rstrip()
		versiondnld = f.readline()[:-1].rstrip()
		versioncommit = f.readline()[:-1].rstrip()
except (IOError, ValueError):
	print("Couldn't get version info, assuming currentrelease")
	versionname = "currentrelease"
	versionsha = 'none'
	versiondnld = 'none'
	versioncommit = 'none'

try:  # if network is down or other error occurs just skip for now rather than blow up
	sha, c = githubutil.GetSHA(versionname)
	# logsupport.Logs.Log('sha: ',sha, ' cvshha: ',config.versionsha,severity=ConsoleDetail)
	if sha != versionsha and sha != 'no current sha':
		print('Current hub version different')
		print('Running (' + versionname + '): ' + versionsha + ' of ' + versioncommit)
		print('Getting: ' + sha + ' of ' + c)
		githubutil.StageVersion(exdir, versionname, 'Offline Dnld')
		githubutil.InstallStagedVersion(exdir)
		print("Staged version installed in " + exdir)
	elif sha == 'no current sha':
		print('No sha for autoversion: ' + versionname)
	else:
		print("sha already matches")
		pass
except Exception as e:
	print("Got exception: " + repr(e))
