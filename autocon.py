#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from datetime import datetime
from json import loads
from sys import argv
from serial import Serial
from automated import Automated, AutoSartano, AutoHue, AutoLG
from scheduler import eventScheduler, event
from stackable.stackable import StackableError
from stackable.network import StackableSocket, StackablePacketAssembler
from stackable.utils import StackableJSON
from stackable.stack import Stack
from runnable.network import RunnableServer, RequestObject

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
		s.actions = {}
		s.scheduler = eventScheduler()
		s.prepare()
		s.loadEvents()

	def listAutomators(self):
		return self.automators

	def listEvents(self):
		return self.events

	def broadcastStatus(self):
		x = auto.list()
		y = {}
		for i in x:
			y[x[i].name] = {'type': x[i].type, 'state': x[i].state}
		pushToAll({'type': 'deviceState', 'payload': y})

	def on(self, key):
		if key == 'ALL':
			for i in self.automators:
				self.automators[i].on()
				self.automators[i].state = 'on'
		else:
			self.automators[key].on()
			self.automators[key].state = 'on'
		self.broadcastStatus()

	def off(self, key):
		if key == 'ALL':
			for i in self.automators:
				self.automators[i].off()
				self.automators[i].state = 'off'
		else:
			self.automators[key].off()
			self.automators[key].state = 'off'
		self.broadcastStatus()

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
			if _id not in self.actions: return

			for action in self.actions[_id]['actions']:
				print('[AUTOMATOR] Setting state of %s to %s' % (action['id'], action['state']))
				self.automators[action['id']].set_state(action['state'])
				self.broadcastStatus()
		self.scheduler.listen(handleEvent)

	def loadEvents(self):
		with open(self.eventfile) as f:
			fevents = loads(f.read())
		for i in fevents:
			timing = datetime.now().replace(hour=i['time']['hours'], minute=i['time']['minutes'], second=0, microsecond=0)
			_id = self.scheduler.getNewID()
			e = event(timing, t='daily', _id=_id)
			self.events.append(e)
			self.actions[_id] = i
			self.scheduler.createEvent(e)

auto = AutoHome(serfile, hwfile, eventFile)

clients = []
def pushToAll(d):
	for i in clients:
		i.write(d)

class Connection(RequestObject):
	def init(self):
		self.stack = Stack((StackableSocket(sock=self.conn),
		                   StackablePacketAssembler(),
		                   StackableJSON()))
		clients.append(self.stack)

	def parse(self, a):
		if 'op' in a:
			if a['op'] == 'list':
				x = auto.listAutomators()
				y = {}
				for i in x:
					y[x[i].name] = {'type': x[i].type, 'state': x[i].state}
				return {'type': 'deviceState', 'payload': y }
			elif a['op'] == 'events':
				x = auto.listEvents()
				y = {}
				for i in x:
					t = i.time
					if type(t) == datetime: # Only return absolute stuff for now...
						y[i.id] = {'type': i.type, 'year':t.year,'month':t.month,'day':t.day,'hour': t.hour,'minute':t.minute,'second':t.second}
					else:
						y[i.id] = {'type': i.type}
				return {'type': 'eventState', 'payload': y}
			elif a['op'] == 'on':
				auto.on(a['name'])
				return {'type':'info', 'payload': {'status': 'ok'}}
			elif a['op'] == 'off':
				auto.off(a['name'])
				return {'type':'info', 'payload': {'status': 'ok'}}
		return {'type':'info', 'payload': {'status': 'error'}}

	def destroy(self):
		try:
			clients.remove(self.stack)
			self.stack.close()
			del self.stack
		except:
			pass

	def receive(self):
		try:
			obj = self.stack.poll()
			if obj != None:
				print("[AUTOMATOR] Received:", obj)
				self.stack.write(self.parse(obj))
			return True
		except StackableError:
			return False
a = RunnableServer({'reqObj': Connection, 'port': listenPort})
a.execute()
