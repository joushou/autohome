#!/usr/bin/python3
from __future__ import print_function, absolute_import
from socket import timeout, socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SO_KEEPALIVE
from socket import error as sock_error
from select import poll, POLLPRI, POLLIN, POLLHUP, POLLERR
from select import error as sel_erro
from json import loads, dumps
#  TCP glue for scheduler
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
			scheduler.createEvent(event(timing, t=args['type'], args=args, _id=_id))
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
