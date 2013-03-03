#!/usr/bin/python2.7

import datetime
import time
import threading
import json
import pprint
from dateutil.rrule import *
import serial

eventFile = "eventProtocol.json"

A       = 3
B       = 2
C       = 1
D       = 0
EXT     = 127

def switcher(id, state):
        ser.write(chr(state<<7|id))

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)


class eventScheduler(threading.Thread):
	def run(self):
		self.internalList = []
		self.reloadEvents()

		while 1:
			self.handleEvents()
			next = self.nextEvent()
			if next < 60:
				time.sleep(next+1)
			else:
				time.sleep(60)

	def reloadEvents(self):
		with open(eventFile) as f:
			self.events = json.loads(f.read())
		self.internalList = []
		for el in self.events:
			self.updateEvent(el)


	def updateEvent(self, event):
		self.internalList.append(	{
										"event": event,
										"datetime": rrule(DAILY, count=1, byhour=event['time']['hours'], byminute=event['time']['minutes'], bysecond=0)[0]
									})

	def nextEvent(self):
		secs = 0
		for event in self.internalList:
			temp = (event['datetime'] - datetime.datetime.now()).seconds
			if temp > secs:
				secs = temp
		return secs		

	def handleEvents(self):
		for idx, event in enumerate(self.internalList):
			if event['datetime'] < datetime.datetime.now() + datetime.timedelta(seconds=1):
				print "Executing event " + event['event']['name']

				for el in event['actions']:
					switcher(el['id'], el['state'])
				self.internalList.pop(idx)
				self.updateEvent(event['event'])

scheduler = eventScheduler()
scheduler.start()