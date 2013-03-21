#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from datetime import datetime
from json import loads, dumps
from serial import Serial
from SocketServer import BaseRequestHandler, TCPServer
from socket import timeout
from sys import argv
from automated import Automated, AutoSartano, AutoHue, AutoLG
from scheduler import eventScheduler, event

serfile = argv[1]
hwfile = argv[2]
eventFile = argv[3]
listenPort = int(argv[4])

class AutoHome(object):
	def __init__(s, serfile, hwfile, eventfile):
		s.serfile = serfile
		s.hwfile = hwfile
		s.eventfile = eventfile
		s.automators = {}
		s.events = []
		s.scheduler = eventScheduler()
		s.prepare()
		s.loadEvents()

	def list(self):
		return self.automators

	def on(self, key):
		if key == 'ALL':
			for i in self.automators:
				i.on()
				i.state = 'on'
		else:
			self.automators[key].on()

	def off(self, key):
		if key == 'ALL':
			for i in self.automators:
				i.off()
				i.state = 'off'
		else:
			self.automators[key].off()

	def dim(self, key, dim):
		self.automators[key].dim(dim)
		self.automators[key].state = dim

	def prepare(self):
		ser = Serial(serfile, 9600, timeout=1)
		def switcher(_id, state):
			ser.write(chr(state<<7|_id))

		with open(hwfile) as f:
			x = loads(f.read())
		for i in x:
			if i['type'] == 'AutoSartano':
				self.automators[i['name']] = AutoSartano(i['params']['id'], switcher)
			if i['type'] == 'AutoHue':
				self.automators[i['name']] = AutoHue(**i['params'])
			if i['type'] == 'AutoLG':
				self.automators[i['name']] = AutoLG('/dev/ttyS0')
			self.automators[i['name']].name = i['name']
			self.automators[i['name']].type = i['type']

		def handleEvent(_id):
			for i in self.events:
				if i['id'] == _id:
					for action in i['actions']:
						print('[AUTOMATOR] Setting state of %s to %s' % (action['id'], action['state']))
						self.automators[action['id']].set_state(action['state'])
					break
		self.scheduler.listen(handleEvent)

	def loadEvents(self):
		with open(self.eventfile) as f:
			self.events = loads(f.read())
		for i in self.events:
			timing = datetime.now().replace(hour=i['time']['hours'], minute=i['time']['minutes'], second=0, microsecond=0)
			i['id'] = self.scheduler.getNewID()
			self.scheduler.createEvent(event(timing, t='daily', _id=i['id']))

auto = AutoHome(serfile, hwfile, eventFile)

class TCPHandler(BaseRequestHandler):
	def parseData(self, data):
		part = data.partition('_')
		if part[2] == 'ON':
			auto.on(part[0])
		elif part[2] == 'OFF':
			auto.off(part[0])
		else:
			auto.dim(part[0], int(part[2]))

	def parseJSON(self, data):
		a = loads(data)
		if 'op' in a:
			if a['op'] == 'list':
				x = auto.list()
				y = {}
				for i in x:
					y[x[i].name] = {'type': x[i].type, 'state': x[i].state}
				return dumps(y)
			elif a['op'] == 'on':
				auto.on(a['name'])
				return dumps({'status': 'ok'})
			elif a['op'] == 'off':
				auto.off(a['name'])
				return dumps({'status': 'ok'})
		return dumps({'status': 'error'})

	def handle(self):
		self.request.settimeout(1)
		print("[AUTOMATOR] Connection from " + self.client_address[0])
		try:
			self.data = self.request.recv(10240)
			print ("[AUTOMATOR] {} wrote:".format(self.client_address[0]))
			print (self.data)
			self.request.sendall(self.parseJSON(self.data))
		except timeout:
			self.request.sendall("TIMEOUT\n")

	def finish(self):
		print("[AUTOMATOR] Connection closed")


TCPServer.allow_reuse_address = True
server = TCPServer(('0.0.0.0', listenPort), TCPHandler)

server.serve_forever()
