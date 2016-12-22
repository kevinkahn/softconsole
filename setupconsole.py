import os
import pwd, grp
import githubutil as U

# decide when/how to call
# handle failure case - don't want to leave system with no code


# Set up directories

piuid = pwd.getpwnam('pi')[2]
pigrp = grp.getgrnam('pi')[2]
for pdir in ('Console', 'consolestable', 'consolebeta', 'consolerem'):
	os.mkdir(pdir)
	os.chown(pdir, piuid, pigrp)

if os.path.exists('homesystem'):
	# personal system
	U.StageVersion('consolestable', 'homerelease', 'InitialInstall')
else:
	U.StagedVersion('consolestable', 'currentrelease', 'InitialInstall')
U.InstallStagedVersion('consolestable')

U.StageVersion('consolebeta', 'currentbeta', 'InitialInstall')
U.InstallStagedVersion('consolebeta')

"""
d = '/home/pi/tester' # should be either where I'm running from  console.exdir/.. then /consolestable or consolebeta
StageVersion(d,'homerelease','Autoinstalled')
InstallStagedVersion(d)

check version current
 reads local version info, uses 1st line to query github, compares sha returns match or not

how do we keep any notion of release type outside the program? for stable just use the version info and seed it to be homerelease or currentrelease
for beta probably can't - so how do we get the right value in the release info for the beta directory?  in use beta have a script item do it?

someplace check that staged version has a console.py before switching to it (safety)


"""
