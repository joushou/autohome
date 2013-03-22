#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from datetime import datetime
from serial import Serial
from json import loads
from sys import argv
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
			self.automators[key].state = 'on'

	def off(self, key):
		if key == 'ALL':
			for i in self.automators:
				i.off()
				i.state = 'off'
		else:
			self.automators[key].off()
			self.automators[key].state = 'off'

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

class Connection(RequestObject):
	def init(self):
		self.stack = Stack((StackableSocket(sock=self.conn),
		                   StackablePacketAssembler(),
		                   StackableJSON()))

	def parse(self, a):
		if 'op' in a:
			if a['op'] == 'list':
				x = auto.list()
				y = {}
				for i in x:
					y[x[i].name] = {'type': x[i].type, 'state': x[i].state}
				return y
			elif a['op'] == 'on':
				auto.on(a['name'])
				return {'status': 'ok'}
			elif a['op'] == 'off':
				auto.off(a['name'])
				return {'status': 'ok'}
		return {'status': 'error'}

	def destroy(self):
		try:
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
