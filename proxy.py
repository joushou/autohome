from __future__ import print_function, absolute_import, unicode_literals, division
from runnable.network import RunnableServer, RequestObject
from stackable.network import StackableSocket, StackablePacketAssembler
from stackable.stack import Stack
from stackable.stackable import StackableError
from threading import Thread

magics = {}

class BackendConnection(RequestObject):
	def init(self):
		self.ip = self.conn.getpeername()[0]
		print('[B] New connection:\t\t', self.ip)
		self.stack = Stack((StackableSocket(sock=self.conn),StackablePacketAssembler(acceptAllMagic=True)))
		self.mgc = None

	def write(self, obj):
		self.stack.write(obj)

	def destroy(self):
		try:
			print('[B] Closing connection:\t\t', self.ip)
			self.stack.close()
			magics[self.mgc].remove(self)
			if len(magics[self.mgc]) == 0:
				del magics[self.mgc]
		except:
			pass

	def receive(self):
		try:
			obj = self.stack.poll()
			if obj != None:
				if self.mgc == None:
					k = self.stack[1]
					self.mgc = k.hdr
					k.sndhdr = self.mgc
					k.magics = [self.mgc]
					k.acceptAllMagic = False

					if self.mgc not in magics:
						magics[self.mgc] = []

					print('[B] Magic identified:\t\t', self.mgc, "for:", self.ip)
					magics[self.mgc].append(self)

				x = magics[self.mgc]
				for ix in x:
					if ix is not self:
						try:
							print("[B] ("+str(self.ip)+"->"+str(ix.ip)+"):\t", obj)
							ix.write(obj)
						except StackableError:
							ix.destroy()
							magics[self.mgc].remove(ix)
			return True
		except StackableError:
			return False

RunnableServer({'reqObj': BackendConnection, 'port': 9995}).execute()
