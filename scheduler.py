#!/usr/bin/python2.7
from __future__ import print_function
from time import mktime, time, sleep
from threading import Thread
import json
from dateutil.rrule import rrule, DAILY
from serial import Serial
import SocketServer, socket

eventFile = "eventProtocol.json"
serfile   = '/dev/ttyUSB0'

# If client has not send any data after this number of secs, connection is closed.
requestTimeout = 1

# TCP port to listen on
listenPort = 9993

A       = 3
B       = 2
C       = 1
D       = 0
EXT     = 127

def switcher(id, state):
   ser.write(chr(state<<7|id))

def allOff():
	switcher(A,0)
	switcher(B,0)
	switcher(C,0)
	switcher(D,0)
	switcher(EXT,0)

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
scheduler.start()

class TCPHandler(SocketServer.BaseRequestHandler):
	def parseData(self, data):
		parts = data.split(':')

		setOptions = []
		returnString = ""

		for element in parts:
			subparts = element.split('=')
			if len(subparts) == 2:
				options[subparts[0]] = subparts[1]
				if subparts[0] not in setOptions:
					setOptions.append(subparts[0])

		commands = {
			"A_ON": lambda: switcher(A, 1),
			"B_ON": lambda: switcher(B, 1),
			"C_ON": lambda: switcher(C, 1),
			"D_ON": lambda: switcher(D, 1),
			"EXT_ON": lambda: switcher(EXT, 1),
			"A_OFF": lambda: switcher(A, 0),
			"B_OFF": lambda: switcher(B, 0),
			"C_OFF": lambda: switcher(C, 0),
			"D_OFF": lambda: switcher(D, 0),
			"EXT_OFF": lambda: switcher(EXT, 0),
			"ALL_OFF": lambda: allOff()
		}
		parts[0] = parts[0].upper()
		if parts[0] in commands:
			returnString = commands[parts[0]]()
		else:
			returnString = "INVALID"

		if not returnString:
			returnString = "OK"

		for i in setOptions:
			returnString += ":" + i + "=" + options[i]
		return returnString + "\n"

	def handle(self):
		self.request.settimeout(requestTimeout)
		print("Connection from " + self.client_address[0])
		try:
			self.data = self.request.recv(1024).strip()
			print ("{} wrote:".format(self.client_address[0]))
			print (self.data)
			self.request.sendall(self.parseData(self.data))
		except socket.timeout:
			self.request.sendall("TIMEOUT\n")

	def finish(self):
		print("Connection closed")

SocketServer.TCPServer.allow_reuse_address = True
server = SocketServer.TCPServer(('0.0.0.0', listenPort), TCPHandler)

server.serve_forever()
