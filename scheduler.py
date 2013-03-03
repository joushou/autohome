#!/usr/bin/python2.7

import datetime
import time
import threading
import json
import pprint
from dateutil.rrule import *

eventFile = "eventProtocol.json"

class eventScheduler(threading.Thread):
	def run(self):
		self.internalList = []
		self.reloadEvents()

		while True:
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
			self.internalList.append(self.createEvent(el))

	def createEvent(self, event):
		return { "event": event,
					"datetime": rrule(DAILY, count=1, byhour=event['time']['hours'], byminute=event['time']['minutes'], bysecond=0)[0]}

	def nextEvent(self):
		secs = 0
		for event in self.internalList:
			temp = (event['datetime'] - datetime.datetime.now()).seconds
			if temp > secs:
				secs = temp
		return secs

	def handleEvents(self):
		tmp = self.internalList
		for idx, event in enumerate(tmp):
			if event['datetime'] < datetime.datetime.now() + datetime.timedelta(seconds=1):
				print('Executing event', event['event']['name'])
				self.internalList[idx] = self.createEvent(event['event'])

scheduler = eventScheduler()
scheduler.start()
