#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from datetime import datetime
from sys import argv
from serial import Serial
from automated import Automated, AutoSartano, AutoHue, AutoLG, AutoTunes
from scheduler import eventScheduler, event
from stackable.stackable import StackableError
from stackable.network import StackableSocket, StackablePacketAssembler
from stackable.utils import StackableJSON, StackablePoker
from stackable.stack import Stack
from time import sleep
import traceback, pickle, json

serfile = argv[1]
hwfile = argv[2]
eventFile = argv[3]
server = argv[4]
serverPort = int(argv[5])
magic = (int(argv[6], 16), int(argv[7], 16), int(argv[8], 16), int(argv[9], 16))

stack = None

class AutoEvent(object):
	def __init__(self, name, event, triggers):
		self.name = name
		self.event = event
		self.triggers = triggers

class AutoHome(object):
	def __init__(s, serfile, hwfile, eventfile):
		s.serfile = serfile
		s.hwfile = hwfile
		s.eventfile = eventfile
		s.automators = {}
		s.events = []
		s.scheduler = eventScheduler()
		s.prepare()
		s.loadStoredEvents()

	def listAutomators(self):
		return self.automators

	def listEvents(self):
		return self.events

	def listActions(self, _id):
		return self.actions[_id]

	def broadcastStatus(self):
		y = []
		for i in self.automators:
			y.append({'type': self.automators[i].type, 'state': self.automators[i].state, 'name': self.automators[i].name})
		if stack != None:
			stack.write({'type': 'deviceState', 'payload': y})

	def broadcastEvents(self):
		ev = []
		for i in self.events:
			y = {'name': i.name, 'triggers': i.triggers, 'event_dispatcher': i.event.event_dispatcher, 'active': i.event.active}
			y['parameters'] = {'hour': i.event.time.hour, 'minute': i.event.time.minute, 'second': i.event.time.second, 'rec': i.event.type, 'days': []}
			ev.append(y)
		if stack != None:
			stack.write({'type': 'eventState', 'payload': ev})

	def broadcastState(self, s):
		if stack != None:
			stack.write({'type': 'partialDeviceState', 'payload': {'type': s.type, 'state': s.state, 'name': s.name}})

	def on(self, key):
		try:
			if key == 'ALL':
				for i in self.automators:
					self.automators[i].on()
				self.broadcastStatus()
			else:
				self.automators[key].on()
				self.broadcastState(self.automators[key])
		except ValueError:
			pass

	def off(self, key):
		try:
			if key == 'ALL':
				for i in self.automators:
					self.automators[i].off()
				self.broadcastStatus()
			else:
				self.automators[key].off()
				self.broadcastState(self.automators[key])
		except ValueError:
			pass

	def dim(self, key, dim):
		try:
			self.automators[key].dim(dim)
			self.automators[key].state = dim
		except ValueError:
			pass

	def disableEvent(self, _id):
		for i in self.events:
			if i.name == _id:
				self.scheduler.disableEvent(i.event)
		self.broadcastEvents()

	def enableEvent(self, _id):
		for i in self.events:
			if i.name == _id:
				self.scheduler.enableEvent(i.event)
		self.broadcastEvents()

	def prepare(self):
		ser = Serial(serfile, 9600, timeout=1)
		def switcher(_id, state):
			ser.write(chr(state<<7|_id))

		with open(hwfile) as f:
			x = json.loads(f.read())
		for i in x:
			if i['type'] == 'AutoSartano':
				self.automators[i['name']] = AutoSartano(i['params']['id'], switcher)
			if i['type'] == 'AutoHue':
				self.automators[i['name']] = AutoHue(**i['params'])
			if i['type'] == 'AutoLG':
				self.automators[i['name']] = AutoLG('/dev/ttyS0')
			if i['type'] == 'AutoTunes':
				self.automators[i['name']] = AutoTunes()
			self.automators[i['name']].name = i['name']
			self.automators[i['name']].type = i['type']

		def handleEvent(ev):
			for aev in self.events:
				if aev.event is ev:
					for trigger in aev.triggers:
						if trigger['state'] == 'on':
							self.on(trigger['name'])
						elif trigger['state'] == 'off':
							self.off(trigger['name'])
						self.broadcastState(self.automators[trigger['name']])
					break
		self.scheduler.listen(handleEvent)

	def loadStoredEvents(self):
		with open(self.eventfile) as f:
			a = f.read()
			if a:
				self.events = pickle.loads(a)
			else:
				self.events = []
		for i in self.events:
			self.scheduler.createEvent(i.event)

	def storeEvents(self):
		with open(self.eventfile, "w") as f:
			f.write(pickle.dumps(self.events))

	def clearEvent(self, name):
		aev = None
		for i in self.events:
			if i.name == name:
				aev = i
				break
		else:
			return

		self.scheduler.clearEvent(aev.event)
		self.events.remove(aev)
		self.broadcastEvents()
		self.storeEvents()

	def registerEvent(self, name, dispatcher, parameters, triggers):
		if dispatcher == 'scheduler':
			timing = datetime.now().replace(hour=parameters['hour'], minute=parameters['minute'], second=parameters['second'], microsecond=0)
			ev = event(timing, t=parameters['rec'])
			self.scheduler.createEvent(ev)
		else:
			raise RuntimeError('Dispatcher not supported')
		aev = AutoEvent(name, ev, triggers)
		self.events.append(aev)
		self.broadcastEvents()
		self.storeEvents()

auto = AutoHome(serfile, hwfile, eventFile)

def parse(a):
	if 'type' in a:
		p = a['payload']
		if a['type'] == 'info':
			if p['infoType'] == 'toggles':
				auto.broadcastStatus()
				return {'type': 'info', 'payload': {'status': 'ok'}}
			elif p['infoType'] == 'events':
				auto.broadcastEvents()
				return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'register_event':
			auto.registerEvent(p['name'], p['event_dispatcher'], p['parameters'], p['triggers'])
			return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'update_event':
			auto.clearEvent(p['old_name'])
			auto.registerEvent(p['name'], p['event_dispatcher'], p['parameters'], p['triggers'])
			return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'remove_event':
			auto.clearEvent(p['name'])
			return {'type': 'info', 'payload': {'status': 'ok'}}

		elif a['type'] == 'disable_event':
			auto.disableEvent(p['name'])
			return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'enable_event':
			auto.enableEvent(p['name'])
			return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'on':
			auto.on(p['name'])
			return {'type':'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'off':
			auto.off(p['name'])
			return {'type':'info', 'payload': {'status': 'ok'}}
	return {'type':'info', 'payload': {'status': 'error'}}

while 1:
	try:
		stack = Stack((StackableSocket(ip=server, port=serverPort), StackablePacketAssembler(magics=[magic]), StackableJSON()))
		stack.write({})
		while 1:
			stack.write(parse(stack.read()))
	except:
		traceback.print_exc()
		sleep(5)
