class Automated(object):
	def __init__(self):
		self.state = 'off'

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

import urllib2
from json import dumps
class AutoHue(Automated):
	def __init__(self, ip, key, n):
		super(AutoHue, self).__init__()
		self.ip = ip
		self.key = key
		self.n = n

	def send(self, w):
		url = 'http://'+self.ip+'/api/'+self.key+'/lights/'+str(self.n)+'/state'
		data = dumps(w)
		opener = urllib2.build_opener(urllib2.HTTPHandler)
		request = urllib2.Request(url, data=data)
		request.get_method = lambda: 'PUT'
		url = opener.open(request)
		print(url, data)
		return url.read()

	def on(self):
		self.send({'on': True})

	def off(self):
		self.send({'on': False})

	def dim(self, s):
		self.send({'on': True, 'bri': int(s*2.54)})
