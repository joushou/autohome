#!/usr/bin/python2.7
from __future__ import print_function
from time import mktime, time, sleep
from threading import Thread
import json
from dateutil.rrule import rrule, DAILY
from serial import Serial

eventFile = "eventProtocol.json"
serfile   = '/dev/ttyUSB0'

A       = 3
B       = 2
C       = 1
D       = 0
EXT     = 127

def switcher(id, state):
   ser.write(chr(state<<7|id))

ser = Serial(serfile, 9600, timeout=1)

class eventScheduler(Thread):
	def run(self):
		self.internalList = []
		self.reloadEvents()

		while True:
			next = self.handleEvents()
			if next < 60:
				sleep(next)
			else:
				sleep(60)

	def reloadEvents(self):
		with open(eventFile) as f:
			self.events = json.loads(f.read())
		self.internalList = []

		for el in self.events:
			self.internalList.append(self.createEvent(el))

	def createEvent(self, event):
		return { "event": event,
					"timestamp": mktime(rrule(DAILY, count=1, byhour=event['time']['hours'], byminute=event['time']['minutes'], bysecond=0)[0].timetuple())}

	def handleEvents(self):
		tmp = self.internalList
		next = 0
		for idx, event in enumerate(tmp):
			t = event['timestamp'] - time()
			if t <= 0:
				print('Executing', event['event']['name'])
				for el in event['event']['actions']:
					switcher(el['id'], el['state'])
				self.internalList[idx] = self.createEvent(event['event'])
			elif t > next:
				next = t
		return next+1

scheduler = eventScheduler()
scheduler.run()
