from __future__ import print_function, absolute_import, unicode_literals, division
from runnable.network import RunnableServer, RequestObject
from stackable.network import StackableSocket, StackablePacketAssembler
from stackable.stack import Stack
from stackable.stackable import StackableError
from threading import Thread

magics = {}

class BackendConnection(RequestObject):
	def init(self):
		print('[B] New connection')
		self.stack = Stack((StackableSocket(sock=self.conn),StackablePacketAssembler(acceptAllMagic=True)))
		self.mgc = None
		self.listeners = []

	def write(self, obj):
		self.stack.write(obj)

	def destroy(self):
		try:
			self.stack.close()
			del magics[self.mgc]
		except:
			pass

	def receive(self):
		try:
			obj = self.stack.poll()
			if obj != None:
				if self.mgc == None:
					self.mgc = self.stack[1].hdr
					print('[B] Identified new magic:', self.mgc)
					self.stack[1].sndhdr = self.mgc
					magics[self.mgc] = self
				x = self.listeners
				for ix in x:
					try:
						ix.write(obj)
					except StackableError:
						self.listeners.remove(ix)
			return True
		except StackableError:
			return False

class FrontendConnection(RequestObject):
	def init(self):
		print('[F] New Connection')
		self.stack = Stack((StackableSocket(sock=self.conn),StackablePacketAssembler(acceptAllMagic=True)))

	def write(self, hdr, obj):
		if hdr not in magics: raise StackableError('No such backend')
		if self.stack not in magics[hdr].listeners:
			magics[hdr].listeners.append(self.stack)
			self.stack[1].sndhdr = hdr

		magics[hdr].write(obj)

	def destroy(self):
		try:
			self.stack.close()
			magics[hdr].listeners.remove(self.stack)
		except:
			pass

	def receive(self):
		try:
			obj = self.stack.poll()
			if obj != None:
				self.write(self.stack[1].hdr, obj)
			return True
		except StackableError:
			return False

a = RunnableServer({'reqObj': BackendConnection, 'port': 9995})
b = RunnableServer({'reqObj': FrontendConnection, 'port': 9994})

at = Thread(target=a.execute)
at.daemon = True
at.start()

b.execute()
