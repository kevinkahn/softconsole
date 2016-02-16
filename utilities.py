import os
import sys
import time
import RPi.GPIO as GPIO
import pygame
import fonts

import config

globdoc = {}
moddoc = {}

def interval_str(sec_elapsed):
    d = int(sec_elapsed/(60*60*24))
    h = int((sec_elapsed%(60*60*24))/3600)
    m = int((sec_elapsed%(60*60))/60)
    s = int(sec_elapsed%60)
    return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)


def normalize_label(l):
    return l if not isinstance(l, basestring) else [l]


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


def LocalizeParams(inst, screensection, *args):
    """
    Merge screen specific parameter values into self.<var> entries for the screen
    inst is the screen object (self), screensection is the Section of the config.txt file for this screen,
        args are any global parameters (see globalparams.py) for which local overrides make sense and are used
    after the call there will be self.xxx variables for all relevant paramters
    by convention to create a local parameter with a default value define a variable of name _p_xxx to get an actual
        variable self.xxx
    :param inst:
    :param screensection:
    :param args:
    :return:
    """
    moddict = sys.modules[inst.__class__.__module__].__dict__
    moddoc[inst.__class__.__module__] = {'loc': {}, 'ovrd': []}
    #    print 'Inst:',inst.__dict__
    #    print 'Class:',inst.__class__.__dict__
    #    print 'Module:',moddict
    #    print 'config:',config.__dict__
    lcllist = []
    lclval = []
    for p in moddict:
        if p.startswith('_p_'):
            nametoadd = p.replace('_p_', '', 1)
            if nametoadd not in inst.__dict__:
                lcllist.append(nametoadd)
                lclval.append(moddict[p])
                moddoc[inst.__class__.__module__]['loc'][lcllist[-1]] = (type(lclval[-1]))
    for p in args:
        lcllist.append(p)
        lclval.append(config.__dict__[p])
        moddoc[inst.__class__.__module__]['ovrd'].append(lcllist[-1])
    for i in range(len(lcllist)):
        if lcllist[i] == 'label':  # todo fix this hack
            t = screensection.get(lcllist[i], lclval[i])
            if isinstance(t, basestring):
                t = [t, ]
            inst.__dict__[lcllist[i]] = t
        else:
            inst.__dict__[lcllist[i]] = type(lclval[i])(screensection.get(lcllist[i], lclval[i]))
