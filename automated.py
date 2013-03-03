class Automated(object):
	def __init__(self):
		pass

	def on(self):
		return NotImplemented

	def off(self):
		return NotImplemented

	def set_state(self, s):
		if s == 1 or s == True:
			self.on()
		else:
			self.off()

class AutoSartano(Automated):
	def __init__(self, d, s):
		super(AutoSartano, self).__init__()
		self.d = d
		self.s = s

	def on(self):
		self.s(self.d, True)

	def off(self):
		self.s(self.d, False)

class AutoHue(Automated):
	def __init__(self, ip, key, n):
		super(AutoHue, self).__init__()
		self.ip = ip
		self.key = key
		self.n = n
