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
from stackable.utils import StackableJSON, StackablePoker
from stackable.stack import Stack
from time import sleep
import traceback

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
		s.loadEvents()

	def listAutomators(self):
		return self.automators

	def listEvents(self):
		return self.events

	def listActions(self, _id):
		return self.actions[_id]

	def broadcastStatus(self):
		x = auto.listAutomators()
		y = {}
		for i in x:
			y[x[i].name] = {'type': x[i].type, 'state': x[i].state}
		if stack != None:
			stack.write({'type': 'deviceState', 'payload': y})

	def broadcastState(self, s):
		if stack != None:
			stack.write({'type': 'partialDeviceState', 'payload': {s.name: {'type': s.type, 'state': s.state}}})

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

	def enableEvent(self, _id):
		for i in self.events:
			if i.name == _id:
				self.scheduler.enableEvent(i.event)

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

	def loadEvents(self):
		with open(self.eventfile) as f:
			fevents = loads(f.read())
		for i in fevents:
			self.registerEvent(i['name'], i['event_dispatcher'], i['parameters'], i['triggers'])

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


	def registerEvent(self, name, dispatcher, parameters, triggers):
		if dispatcher == 'scheduler':
			timing = datetime.now().replace(hour=parameters['hour'], minute=parameters['minute'], second=parameters['second'], microsecond=0)
			ev = event(timing, t=parameters['rec'])
			self.scheduler.createEvent(ev)
		else:
			raise RuntimeError('Dispatcher not supported')
		aev = AutoEvent(name, ev, triggers)
		self.events.append(aev)

auto = AutoHome(serfile, hwfile, eventFile)

def parse(a):
	if 'type' in a:
		p = a['payload']
		if a['type'] == 'info':
			if p['infoType'] == 'toggles':
				auto.broadcastStatus()
				return None
			elif p['infoType'] == 'events':
				evs = []
				for i in auto.events:
					y = {'name': i.name, 'triggers': i.triggers, 'event_dispatcher': i.event.event_dispatcher, 'active': i.event.active}
					y['parameters'] = {'hour': i.event.time.hour, 'minute': i.event.time.minute, 'second': i.event.time.second, 'rec': i.event.type, 'days': []}
					evs.append(y)
				return {'type': 'eventState', 'payload': evs}

		elif a['type'] == 'register_event':
			auto.registerEvent(p['name'], p['event_dispatcher'], p['parameters'], p['triggers'])
			return {'type': 'info', 'payload': {'status': 'ok'}}
		elif a['type'] == 'update_event':
			auto.clearEvent(p['name'])
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
		stack = Stack((StackableSocket(ip=server, port=serverPort), StackablePacketAssembler(magics=[magic]), StackablePoker(), StackableJSON()))
		stack.write({})
		while 1:
			stack.write(parse(stack.read()))
	except:
		traceback.print_exc()
		sleep(5)
