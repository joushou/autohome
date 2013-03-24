#!/usr/bin/python3
from __future__ import print_function, absolute_import
from threading import Thread, Event
from datetime import datetime, timedelta

listenPort = 9993

def singleton(cls):
	instances = {}
	def getinstance():
		if cls not in instances:
			instances[cls] = cls()
		return instances[cls]
	return getinstance

class eventInfo(object):
	def __init__(self, reached=False, new_delta=0, skew=0):
		self.reached = reached
		self.delta = new_delta
		self.skew = skew

class event(object):
	event_dispatcher = 'scheduler'
	def __init__(self, _time=None, t='', args=None, _id=0):
		self.time   = _time
		self.cur    = datetime.now()
		self.dtime  = self.cur
		self.last   = None
		self.id     = _id
		self.args   = args
		self.type   = t
		self.active = True
		self.recalc = self.__getattribute__(t)

	def __str__(self):
		return "<event %s %s>" % (str(self.time), self.op)

	def every(self, new):
		if new >= self.dtime:
			old = self.dtime
			self.dtime = self.cur
			while self.dtime < new:
				self.dtime += self.time
			self.last = datetime.now()
			return eventInfo(True, self.dtime - new, old - new)
		else:
			return eventInfo(False, self.dtime - new)

	def daily(self, new):
		if new > self.time:
			old = self.time
			self.time += timedelta(days=1)
			self.last = datetime.now()
			return eventInfo(True, self.time - new, old - new)
		else:
			return eventInfo(False, self.time - new)

	def reg_daily(self, new):
		if new > self.time:
			old = self.time
			if new.isoweekday() < 5:
				self.time += timedelta(days=1)
			else:
				self.time += timedelta(days=8-new.isoweekday())
			self.last = datetime.now()
			return eventInfo(True, self.time - new, old - new)
		else:
			return eventInfo(False, self.time - new)

@singleton
class eventScheduler(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.wait_event = Event()
		self.event_list = []
		self.event_id = 0
		self.listeners = []
		self.daemon = True
		self.start()

	def wake(self):
		self.wait_event.set()

	def listen(self, cb):
		self.listeners.append(cb)

	def unlisten(self, cb):
		self.listeners.remove(cb)

	def run(self):
		while True:
			next = self.handleEvents()
			if next != None:
				next = next.total_seconds()
				print('[SCHEDULER] %d event(s) queued, next wake-up: %fs' % (len(self.event_list), next))
			else:
				print('[SCHEDULER] No events queued, waiting for condition.')
			self.wait_event.wait(next)
			self.wait_event.clear()

	def disableEvent(self, ev):
		ev.active = False

	def enableEvent(self, ev):
		ev.active = True

	def clearEvent(self, ev):
		self.event_list.remove(ev)

	def createEvent(self, event):
		self.event_list.append(event)
		self.wake()
		self.event_id += 1
		event.id = self.event_id
		return event

	def handleEvents(self):
		cur = datetime.now()
		next = None
		x = self.event_list
		for ev in x:
			if not ev.active:
				continue

			t = ev.recalc(cur)
			if t.reached:
				print('[SCHEDULER] Raising event %d, %fs overdue' % (ev.id, abs(t.skew.total_seconds())))
				for i in self.listeners:
					i(ev)

			if t.delta == 0:
				self.event_list.remove(ev)
			elif next == None or t.delta < next:
				next = t.delta
		return next
