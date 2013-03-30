class Automated(object):
	def __init__(self):
		self.state = 'off'

	def on(self):
		return NotImplemented

	def off(self):
		return NotImplemented

	def check(self):
		return NotImplemented

	def set_state(self, s):
		if s == 'on' or s == 1 or s == True:
			self.on()
		else:
			self.off()

class AutoSartano(Automated):
	def __init__(self, d, s):
		super(AutoSartano, self).__init__()
		self.d = d
		self.s = s

	def on(self):
		self.state = 'on'
		self.s(self.d, True)

	def off(self):
		self.state = 'off'
		self.s(self.d, False)

from serial import Serial
class AutoLG(Automated):
	def __init__(self, serialPort):
		self.functions = {
			"dtv": "xb 00 00\x0D",
			"hdmi1": "xb 00 90\x0D",
			"hdmi2": "xb 00 91\x0D",
			"4:3": "kc 00 01\x0D",
			"justscan": "kc 00 09\x0D",
			"reasonableVolume": "kf 00 05\x0D"
		}
		super(AutoLG, self).__init__()
		self.ser = Serial(serialPort, 9600, timeout=1)

	def hasFunction(self, cmd):
		if cmd in self.functions:
			return True
		else:
			return False

	def on(self):
		self.state = 'on'
		self.ser.write("ka 00 01\x0D")
	def off(self):
		self.state = 'off'
		self.ser.write("ka 00 00\x0D")
	def custom(self, cmd):
		self.ser.write(self.functions[cmd])

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
		self.state = 'on'
		self.send({'on': True})

	def off(self):
		self.state = 'off'
		self.send({'on': False})

	def dim(self, s):
		self.send({'on': True, 'bri': int(s*2.54)})

from os import system
class AutoTunes(Automated):
		def __init__(self):
			super(AutoTunes, self).__init__()

		def osa(self, s):
			system('osascript -e \'%s\'' % s)

		def tell(self, a, s):
			self.osa('''
tell application "%a"
	%s
end tell
			         ''' % (a,s))

		def on(self):
			self.state = 'on'
			self.tell('iTunes', 'play')

		def off(self):
			self.state = 'off'
			self.tell('iTunes', 'stop')
