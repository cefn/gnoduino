# gnoduino - Python Arduino IDE implementation
# Copyright (C) 2010  Lucian Langa
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import config
import glob
import misc
import time
import serial

import gettext
_ = gettext.gettext

class sconsole:
	def __init__(self):
		"""9600 8N1"""
		self.serial = serial.Serial(
			port=None,
			baudrate=9600,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS
		)

	def __del__(self):
		self.serial.close()

	def tryPort(self, port):
		return serial.Serial(port)

	def scan(self):
		"""scan for available ports. return a list of device names."""
		ports = []
		tryports = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/rfcomm*')
		for i in tryports:
			try:
				s = serial.Serial(i)
				ports.append(s.portstr)
				s.close()
			except serial.SerialException:
				pass
		return ports

	def read(self):
		while self.serial.inWaiting() > 0:
			return self.serial.read(self.serial.inWaiting())
		return None


	def updateConsole(self, console):
		b = console.get_buffer()
		cont = self.read()
		if cont:
			print cont
		if cont != None:
			if b and len(cont) > 1:
				cont = unicode(
					cont.replace('\x00', '.').decode('utf-8', 'replace').encode('utf-8'))
				b.insert(b.get_end_iter(), \
					cont)
				console.scroll_mark_onscreen(b.get_insert())
		return True

	def resetBoard(self):
		self.serial.setDTR(False)
		time.sleep(0.1)
		self.serial.setDTR(True)

	def clearConsole(self, w, console):
		b = console.get_buffer()
		b.delete(b.get_start_iter(), b.get_end_iter())
		b.set_text("")

	def getBaudrates(self):
		return [i[0] for i in self.serial.getSupportedBaudrates() if i[1] >= 300 and i[1] <= 1150000]
	def getConfigSerialPort(self, notify, output):
		if config.cur_serial_port == -1:
			misc.printError(None, output, \
				_("Serial port not configured!\nUse Tools->Serial Port to configure port."))
			return -1
		else:
			return config.cur_serial_port

