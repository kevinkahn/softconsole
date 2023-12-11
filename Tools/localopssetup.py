import os
import shutil
import config
import subprocess


def PreOp():
	if not os.path.exists(config.sysStore.HomeDir + '/homesystem'):
		print('Not home system')
		return
	# noinspection PyBroadException
	try:
		os.mkdir(config.sysStore.HomeDir + '/photos')
	except Exception:
		pass
	# noinspection PyBroadException
	try:
		os.mkdir(config.sysStore.HomeDir + '/.exconfs')
	except Exception:
		pass
	if not os.path.exists('/etc/fstab.sav'):
		shutil.copyfile('/etc/fstab', '/etc/fstab.sav')
	with open('/etc/fstab.sav') as fin:
		with open('/etc/fstab', 'w') as fout:
			for ln in fin:
				if 'cifs' not in ln:
					fout.write(ln)
			fout.write(
				"//pdxhome.pdxhome/data/ConsolePhotos /home/pi/photos cifs username=kevin,password=xxx,iocharset=utf8,ro 0 0\n")
			fout.write(
				"//pdxhome.pdxhome/data/PythonProjects/softconsole/example\\040configs "
				"/home/pi/.exconfs cifs username=kevin,password=xxx,iocharset=utf8,ro 0 0\n")
		subprocess.run(["mount", "-a"])
