"""
This file holds utility functions that have no dependencies on other console code.
Avoids import loops
"""
import time

import webcolors
import importlib, os
import config


def importmodules(dir: str):
	# dir of form relative path name
	importlist = {}
	path = dir.split('/')
	if path[0] == '': del path[0]
	pypath = '.'.join(path) + '.'
	impdir = '/'.join(path)
	# print('Dir {} Digested {} Path {}'.format(dir, pypath, impdir))
	for modulename in os.listdir(os.getcwd() + '/' + impdir):
		if '__' not in modulename:
			splitname = os.path.splitext(modulename)
			if splitname[1] == '.py':
				#print('import {}{} using {}'.format(pypath, splitname[0], modulename))
				importlist[splitname[0]] = importlib.import_module(pypath + splitname[0])
	return importlist


def wc(clr, factor=0.0, layercolor=(255, 255, 255)):
	lc = webcolors.name_to_rgb(layercolor.lower()) if isinstance(layercolor, str) else layercolor
	if isinstance(clr, str):
		try:
			v = webcolors.name_to_rgb(clr.lower())
		except ValueError:
			# logsupport.Logs.Log('Bad color name: ' + str(clr), severity=ConsoleWarning)
			v = webcolors.name_to_rgb('black')
	else:
		v = clr
	try:
		return v[0] + (lc[0] - v[0]) * factor, v[1] + (lc[1] - v[1]) * factor, v[2] + (lc[2] - v[2]) * factor
	except Exception as E:
		print('wc: {}'.format(E))
		print(v, lc, clr, layercolor)


def interval_str(sec_elapsed, shrt=False):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	if d != 0:
		if shrt:
			return "{} dys {:>02d}:{:>02d}:{:>02d}".format(d, h, m, s)
		else:
			return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)
	elif h != 0:
		return "{:>02d}hrs {:>02d}mn {:>02d}sec".format(h, m, s)
	else:
		return "{:>02d}mn {:>02d}sec".format(m, s)


def BoolTrueWord(v):
	if v is None: return False
	if isinstance(v, bool): return v
	try:
		return v.lower() in ('true', 'on', 'yes')
	except Exception as e:
		print("Error1: {}".format(v))

def BoolFalseWord(v):
	if v is None: return True
	if isinstance(v, bool): return not v
	try:
		return v.lower() in ('false', 'off', 'no')
	except Exception as e:
		print("Error2: {}".format(v))

def TreeDict(d, args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		temp = d[args[0]]
		#temp = getattr(d,args[0])
		if isinstance(temp, str) and temp.isdigit():
			temp = int(temp)
		else:
			try:
				temp = float(temp)
			except (ValueError, TypeError):
				pass
		return temp
	else:
		return TreeDict(d[args[0]], args[1:])
		#return TreeDict(getattr(d,args[0]),args[1:])

import string
class PartialFormatter(string.Formatter):
	def __init__(self, missing='--', bad_fmt='--'):
		self.missing, self.bad_fmt = missing, bad_fmt

	def get_field(self, field_name, args, kwargs):
		# Handle a key not found
		try:
			val = super().get_field(field_name, args, kwargs)
		except (KeyError, AttributeError):
			val = None, field_name
		return val

	def format_field(self, value, spec):
		# handle an invalid format
		if value is None: return self.missing
		try:
			return super().format_field(value, spec)
		except ValueError:
			if self.bad_fmt is not None:
				return self.bad_fmt
			else:
				raise


fmt = PartialFormatter()


# noinspection PyBroadException
isdevsystem = False
def safeprint(*args, **kwargs):
	if isdevsystem or config.sysStore.versionname == 'homerelease':
		try:
			print(time.strftime('%m-%d-%y %H:%M:%S'), *args, **kwargs)
		except OSError:
			with open('/home/pi/Console/disconnectederrors.log', 'a') as f:
				print(*args, **kwargs, file=f)

def RepresentsInt(s):
	try:
		int(s)
		return True
	except (ValueError, TypeError):
		return False
'''
class WFormatter(string.Formatter):
	def format_field(self, value, format_spec):
		if format_spec.endswith(('f', 'd')) and value is None:
			return 'n/a'
		elif value is None:
			return 'n/a'
		elif value == -9999.0:
			return 'n/a'
		else:
			return super(WFormatter, self).format_field(value, format_spec)
'''
