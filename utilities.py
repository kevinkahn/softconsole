import os
import sys
import time
import RPi.GPIO as GPIO
import pygame
import fonts
from logsupport import Info, Warning, Error

import config

globdoc = {}
moddoc = {}

def interval_str(sec_elapsed):
    d = int(sec_elapsed/(60*60*24))
    h = int((sec_elapsed%(60*60*24))/3600)
    m = int((sec_elapsed%(60*60))/60)
    s = int(sec_elapsed%60)
    return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)


def scaleW(p):
    return int(round(float(p)*float(config.dispratioW)))


def scaleH(p):
    return int(round(float(p)*float(config.dispratioH)))


def ParseParam(param):
    for p in param.__dict__:
        if '__' not in p:
            p2 = p.replace('_', '', 1) if p.startswith('_') else p
            config.__dict__[p2] = type(param.__dict__[p])(config.ParsedConfigFile.get(p2, param.__dict__[p]))
            globdoc[p2] = type(param.__dict__[p])
            if not p.startswith('_'):
                config.Logs.Log('Param: ' + p + ": " + str(config.__dict__[p2]))


def signal_handler(sig, frame):
    print "Signal: {}".format(sig)
    print "pid: ", os.getpid()
    time.sleep(1)
    pygame.quit()
    print time.time(), "Console Exiting"
    sys.exit(0)


def daemon_died(sig, frame):
    print "CSignal: {}".format(sig)
    if config.DaemonProcess is None:
        return
    if config.DaemonProcess.is_alive():
        print "Child ok"
    else:
        print time.time(), "Daemon died!"
        pygame.quit()
        sys.exit()


def InitializeEnvironment():
    os.environ['SDL_FBDEV'] = '/dev/fb1'
    os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
    os.environ['SDL_MOUSEDRV'] = 'TSLIB'
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    pygame.display.init()
    config.fonts = fonts.Fonts()
    config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)

    config.screenwidth = 240  # todo 2 lines for test only
    config.screenheight = 320

    """
    Scale screen constants
    """
    config.dispratioW = float(config.screenwidth)/float(config.basewidth)
    config.dispratioH = float(config.screenheight)/float(config.baseheight)
    config.horizborder = scaleW(config.horizborder)
    config.topborder = scaleH(config.topborder)
    config.botborder = scaleH(config.botborder)
    config.cmdvertspace = scaleH(config.cmdvertspace)

    print config.dispratioW
    print config.dispratioH
    print config.horizborder
    print config.topborder
    print config.botborder
    print config.cmdvertspace

    config.screen = pygame.display.set_mode((config.screenwidth, config.screenheight), pygame.FULLSCREEN)
    config.screen.fill((0, 0, 0))  # clear screen
    pygame.display.update()
    pygame.mouse.set_visible(False)
    pygame.fastevent.init()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT)
    config.backlight = GPIO.PWM(18, 1024)
    config.backlight.start(100)


def LocalizeParams(inst, configsection, *args, **kwargs):
    """
    Merge screen specific parameter values into self.<var> entries for the class
    inst is the class object (self), configsection is the Section of the config.txt file for this object,
        args are any global parameters (see globalparams.py) for which local overrides make sense and are used
    after the call there will be self.xxx variables for all relevant paramters
    kwargs are locally defined parameters for this object and a default value which also gets added as self.xxx and
        a value is taken from the config section if present
    :param inst:
    :param screensection:
    :param args:
    :param kwargs:
    :return:
    """
    global moddoc
    if not inst.__class__.__name__ in moddoc:
        moddoc[inst.__class__.__name__] = {'loc': {}, 'ovrd': set()}
    lcllist = []
    lclval = []
    for nametoadd in kwargs:
        if nametoadd not in inst.__dict__:
            lcllist.append(nametoadd)
            lclval.append(kwargs[nametoadd])
            moddoc[inst.__class__.__name__]['loc'][lcllist[-1]] = (type(lclval[-1]))
        else:
            print 'why dup', nametoadd
    for nametoadd in args:
        if nametoadd in config.__dict__:
            lcllist.append(nametoadd)
            lclval.append(config.__dict__[nametoadd])
            moddoc[inst.__class__.__name__]['ovrd'].add(lcllist[-1])
        else:
            config.Logs.Log("Obj " + inst.__class__.__name__ + ' attempted import of non-existent global ' + nametoadd,
                            Error)
    for i in range(len(lcllist)):
        inst.__dict__[lcllist[i]] = type(lclval[i])(configsection.get(lcllist[i], lclval[i]))
