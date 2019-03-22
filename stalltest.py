import time

interval = .5
nowtime = time.time()
print('Starting')
'''
while True:
	time.sleep(interval)
	postsleep = time.time()
	delta = postsleep - nowtime
	if delta > interval * 1.2:
		print('Now: {} PostSleep: {} Delta: {}'.format(nowtime, postsleep, delta))
	nowtime = time.time()

print('Ending')
'''

import pygame
pygame.init()
pygame.fastevent.init()

evnt = pygame.event.Event(pygame.USEREVENT,{})


pygame.time.set_timer(evnt.type, 2)

while True:
	ev = pygame.fastevent.wait()
	postwait = time.time()
	delta = postwait - nowtime
	if delta > 2.2:
		print('Now: {} PostSleep: {} Delta: {}'.format(nowtime, postwait, delta))
	nowtime = time.time()
	pygame.time.set_timer(evnt.type, 2)