#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from time import mktime, time, sleep
from threading import Thread
from json import loads
from dateutil.rrule import rrule, DAILY
from serial import Serial
from SocketServer import BaseRequestHandler, TCPServer
from socket import timeout
from sys import argv
from automated import Automated, AutoSartano, AutoHue

serfile = argv[1]
eventFile = argv[2]
listenPort = int(argv[3])
if len(argv) > 4:
	hue_ip = argv[4]
	hue_key = argv[5]

ser = Serial(serfile, 9600, timeout=1)

def switcher(id, state):
   ser.write(chr(state<<7|id))

automators = {
	'A': AutoSartano(3, switcher),
	'B': AutoSartano(2, switcher),
	'C': AutoSartano(1, switcher),
	'D': AutoSartano(0, switcher),
	'EXT': AutoSartano(127, switcher)
}

def allOff():
	for i in automators:
		automators[i].off()

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
			self.events = loads(f.read())
		self.internalList = []

		for el in self.events:
			print('New event:', el)
			self.internalList.append(self.createEvent(el))

	def createEvent(self, event):
		return { "event": event,
					"timestamp": mktime(rrule(DAILY, count=1, byhour=event['time']['hours'], byminute=event['time']['minutes'], bysecond=0)[0].timetuple())}

	def handleEvents(self):
		tmp = self.internalList
		cur = time()
		next = 0
		for idx, event in enumerate(tmp):
			t = event['timestamp'] - cur
			if t <= 0:
				print('Executing', event['event']['name'])
				for el in event['event']['actions']:
					automators[el['id']].set_state(el['state'])
				self.internalList[idx] = self.createEvent(event['event'])
			elif t > next:
				next = t
		return next+1

scheduler = eventScheduler()
scheduler.daemon = True
scheduler.start()

class TCPHandler(BaseRequestHandler):
	def parseData(self, data):
		part = data.partition('_')
		if part[0] == 'ALL':
			for i in automators:
				if part[2] == 'ON':
					automators[i].on()
				else:
					automators[i].off()
		elif part[0] in automators:
			if part[2] == 'ON':
				automators[part[0]].on()
			elif part[2] == 'OFF':
				automators[part[0]].off()
			else:
				try:
					automators[part[0]].dim(int(part[2]))
				except:
					pass
			return 'OK\n'
		else:
			return 'ERROR\n'

	def handle(self):
		self.request.settimeout(1)
		print("Connection from " + self.client_address[0])
		try:
			self.data = self.request.recv(1024).strip()
			print ("{} wrote:".format(self.client_address[0]))
			print (self.data)
			self.request.sendall(self.parseData(self.data))
		except timeout:
			self.request.sendall("TIMEOUT\n")

	def finish(self):
		print("Connection closed")

TCPServer.allow_reuse_address = True
server = TCPServer(('0.0.0.0', listenPort), TCPHandler)

server.serve_forever()
