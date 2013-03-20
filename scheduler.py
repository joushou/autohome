#!/usr/bin/python2.7
from __future__ import print_function, absolute_import
from threading import Thread, Event
from json import loads, dumps
from datetime import date, datetime, timedelta
from serial import Serial
from socket import timeout, socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SO_KEEPALIVE
from socket import error as sock_error
from select import poll, POLLPRI, POLLIN, POLLHUP, POLLERR
from select import error as sel_error

listenPort = 9993

class eventInfo(object):
	def __init__(self, reached=False, new_delta=0, skew=0):
		self.reached = reached
		self.delta = new_delta
		self.skew = skew

class event(object):
	def __init__(self, _time=None, t='', _id=0):
		self.time   = _time
		self.cur    = datetime.now()
		self.dtime  = self.cur
		self.id     = _id
		self.recalc = self.__getattribute__('_'+t)

	def __str__(self):
		return "<event %s %s>" % (str(self.time), self.op)

	def _every(self, new):
		if new >= self.dtime:
			old = self.dtime
			self.dtime = self.cur
			while self.dtime < new:
				self.dtime += self.time
			return eventInfo(True, self.dtime - new, old - new)
		else:
			return eventInfo(False, self.dtime - new)

	def _daily(self, new):
		if new > self.time:
			old = self.time
			self.time += timedelta(days=1)
			return eventInfo(True, self.time - new, old - new)
		else:
			return eventInfo(False, self.time - new)

	def _reg_daily(self, new):
		if new > self.time:
			old = self.time
			if new.isoweekday() < 5:
				self.time += timedelta(days=1)
			else:
				self.time += timedelta(days=8-new.isoweekday())
			return eventInfo(True, self.time - new, old - new)
		else:
			return eventInfo(False, self.time - new)

class eventScheduler(Thread):
	def __init__(self):
		super(eventScheduler, self).__init__()
		self.wait_event = Event()
		self.event_list = []
		self.event_id = 0
		self.listeners = []

	def wake(self):
		self.wait_event.set()

	def listen(self, cb):
		self.listeners.append(cb)

	def unlisten(self, cb):
		self.listeners.remove(cb)

	def run(self):
		while True:
			next = self.handleEvents()
			if next == None: # No events, just sleep
				next = 600
			else:
				next = next.total_seconds()
			print('%d event(s) queued, next wake-up: %fs' % (len(self.event_list), next))
			self.wait_event.wait(next)
			self.wait_event.clear()

	def clearEvent(self, _id):
		x = self.event_list
		for i in x:
			if i.id == _id:
				self.event_list.remove(i)
				self.wake()
				return True
		else:
			return False

	def getNewID(self):
		self.event_id += 1
		return self.event_id

	def createEvent(self, event):
		self.event_list.append(event)
		self.wake()
		return event

	def handleEvents(self):
		cur = datetime.now()
		next = None
		x = self.event_list
		for ev in x:
			t = ev.recalc(cur)
			if t.reached:
				print('Raising event %d, %fs overdue' % (ev.id, t.skew.total_seconds()))
				for i in self.listeners:
					i(ev.id)

			if t.delta == 0:
				self.event_list.remove(ev)
			elif next == None or t.delta < next:
				next = t.delta
		return next

scheduler = eventScheduler()
scheduler.daemon = True
scheduler.start()

#  Everything below this line is the network handling,
#  which is rather... weird at the moment.
########################################################

op_keywords = ['cancel', 'register']
arg_keywords = ['relative', 'id', 'type']
timing_keywords = ['year', 'month','day', 'hour', 'minute', 'second', 'microsecond']

class RequestObject(object):
	def __init__(self, conn):
		self.conn = conn

	def init(self):
		def cb(_id):
			self.conn.sendall(bytes(dumps({'raising':_id}), encoding='utf-8'))
		self.cb = cb
		scheduler.listen(self.cb)

	def receive(self):
		d = self.conn.recv(10240)
		if d == b'':
			return False
		print(d)
		d = loads(d.decode('utf-8'))
		absolute = 'relative' not in d or not d['relative']
		timing = datetime.now().replace(second=0, microsecond=0) if absolute else timedelta(seconds=0)

		op = ''
		args = {}
		for i in d:
			if i in timing_keywords:
				if absolute:
					x = {str(i):d[i]}
					timing = timing.replace(**x)
				else:
					x = {str(i)+'s':d[i]}
					timing += timedelta(**x)
			elif i in op_keywords:
				op = i
			elif i in arg_keywords:
				args[i] = d[i]
			else:
				self.request.sendall(dumps({'error': 'unknown key: %s' % str(i)}))
				return False

		if op == 'register':
			_id = scheduler.getNewID()
			scheduler.createEvent(event(timing, t=args['type'], _id=_id))
			self.conn.sendall(bytes(dumps({'id': _id}), encoding='utf-8'))
		elif op == 'cancel':
			self.conn.sendall(bytes(dumps({'success': scheduler.clearEvent(args['id'])}), encoding='utf-8'))
		return True

	def destroy(self):
		scheduler.unlisten(self.cb)

class RunnableServer(object):
	def execute(self):

		servsock = socket(AF_INET, SOCK_STREAM)
		servsock.setblocking(0)
		servsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		servsock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
		servsock.settimeout(None)

		servfdmap = {servsock.fileno(): servsock}
		clients = {}

		servpoll = poll()
		pollin, pollpri, pollhup, pollerr = POLLIN, POLLPRI, POLLHUP, POLLERR

		def terminate(fd):
			clients[fd].destroy()
			servpoll.unregister(servfdmap[fd])
			del clients[fd]
			del servfdmap[fd]

		servsock.bind(("0.0.0.0", 9993))
		servsock.listen(40)

		servpoll.register(servsock, pollin | pollpri | pollhup | pollerr)

		while True:
			try:
				events = servpoll.poll()
				for fd,flags in events:
					mappedfd = servfdmap[fd]

					if flags & pollin or flags & pollpri:
						if mappedfd is servsock:
							connection, client_address = mappedfd.accept()
							fileno = connection.fileno()
							servfdmap[fileno] = connection
							servpoll.register(connection, pollin | pollpri | pollhup | pollerr)

							clients[fileno] = RequestObject(connection)
							clients[fileno].init()

						else:
							try:
								if not clients[fd].receive():
									terminate(fd)
							except sock_error:
								terminate(fd)
					elif flags & pollhup or flags & pollerr:
						if mappedfd is servsock:
							raise RuntimeError("Server socket broken")
						else:
							terminate(fd)
			except sel_error:
				pass

a = RunnableServer()
a.execute()
