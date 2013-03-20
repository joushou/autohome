#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from datetime import datetime
from json import loads
from serial import Serial
from SocketServer import BaseRequestHandler, TCPServer
from socket import timeout
from sys import argv
from automated import Automated, AutoSartano, AutoHue
from scheduler import eventScheduler, event

serfile = argv[1]
hwfile = argv[2]
eventFile = argv[3]
listenPort = int(argv[4])

ser = Serial(serfile, 9600, timeout=1)
def switcher(id, state):
   ser.write(chr(state<<7|id))

automators = {}

with open(hwfile) as f:
	x = loads(f.read())
for i in x:
	if i['type'] == 'AutoSartano':
		automators[i['name']] = AutoSartano(i['params']['id'], switcher)
	if i['type'] == 'AutoHue':
		automators[i['name']] = AutoHue(**i['params'])

events = []
scheduler = eventScheduler()

def handleEvent(_id):
	global events
	for i in events:
		if i['id'] == _id:
			for action in i['actions']:
				print('[AUTOMATOR] Setting state of %s to %s' % (action['id'], action['state']))
				automators[action['id']].set_state(action['state'])
			break
scheduler.listen(handleEvent)

def loadEvents():
	global events
	with open(eventFile) as f:
		events = loads(f.read())
	for i in events:
		timing = datetime.now().replace(hour=i['time']['hours'], minute=i['time']['minutes'], second=0, microsecond=0)
		i['id'] = scheduler.getNewID()
		scheduler.createEvent(event(timing, t='daily', _id=i['id']))

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
		print("[AUTOMATOR] Connection from " + self.client_address[0])
		try:
			self.data = self.request.recv(1024).strip()
			print ("[AUTOMATOR] {} wrote:".format(self.client_address[0]))
			print (self.data)
			self.request.sendall(self.parseData(self.data))
		except timeout:
			self.request.sendall("TIMEOUT\n")

	def finish(self):
		print("[AUTOMATOR] Connection closed")

loadEvents()

TCPServer.allow_reuse_address = True
server = TCPServer(('0.0.0.0', listenPort), TCPHandler)

server.serve_forever()
