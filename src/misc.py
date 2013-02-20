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

import os
import ConfigParser
import glib
from xdg import Mime
import gtk
import hashlib
import logging
import select
import subprocess
import pango
import time
import tempfile
import gettext
import sys
_ = gettext.gettext

import board
import config
import prefs

LOG_FILENAME = 'arduino.out'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

def get_path(main_path, default=None):
    possible_paths = [
        os.path.join(os.path.expanduser('~/.arduino'), main_path),
        os.path.join(os.getcwd(), main_path),
        os.path.join(sys.prefix, "share", "arduino", main_path),
        os.path.join(sys.prefix, "local", "share", "gnoduino", main_path),
        os.path.join(sys.prefix, "share", "gnoduino", main_path),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    if default:
        return default
    raise SystemExit(_("Unable to locate %s\nArduino SDK missing or broken.") % main_path)

def getArduinoFile(filename):
	return get_path(filename)

def getArduinoPath():
	return get_path("hardware/arduino/cores/arduino")

def getArduinoVariantPath():
	b = board.Board()
	variant = b.getVariant(b.getBoard())
	if variant:
		try:
			return get_path("hardware/arduino/variants/" + variant)
		except:
			hwdir = os.path.dirname(b.getHardwarePath(b.getBoard()))
			return os.path.join(hwdir, "variants", variant)

def getArduinoIncludes():
	includes = ["-I" + getArduinoPath()]
	if getArduinoVersion() >= 100:
		variant = getArduinoVariantPath()
		if variant:
			includes += ["-I" + getArduinoVariantPath()]
	return includes

def getArduinoBootPath():
	return get_path("hardware/arduino/bootloaders")

def getArduinoVersion():
	"""this is far from something accurate but for now
		we just need to differentiate beween 1.0 and pre 1.0
		versions of arduino"""
	try:
		if os.path.isfile(getArduinoFile("hardware/arduino/cores/arduino/Arduino.h")):
			return 100
	except:
		if os.path.isfile(getArduinoFile("hardware/arduino/cores/arduino/WProgram.h")):
			return 22

def getArduinoAPIFile():
	if getArduinoVersion() >= 100:
		return "Arduino.h"
	else:
		return "WProgram.h"

def getArduinoLibsPath():
	return get_path("libraries", default="")

def getArduinoUiPath():
	return get_path("ui", default="")

def getPixmapPath(pixmap):
	return get_path(os.path.join("pixmaps", pixmap))

"""generic function to read Arduino preferences-like file"""

def readArduinoConfFile(confFile):
	conf = []
	try:
		f = open(confFile)
		q = []
		z = []
		for c in f.readlines():
			if c!='\n':
				l = ""
				line =  c.split('\n')[0]
				if line != "" and line[0] != "#":
					l = line.split("=")
					z.append(l)
					q.append(l[0].split(".")[0])

		k = 1
		for i in sorted(set(q), reverse=True):
			w = dict()
			for c in z:
				if c[0].split(".")[0] == i:
					var = c[0].split(".")[-1]
					if var == "name":
						w['name'] = i
						w['desc'] = c[1]
					else:
						w[var] = c[1]
			w['hwpath'] = confFile
			w['id'] = k
			k += 1
			conf.append(w)
		return conf
	except: return None

def readGnoduinoConfFile(confFile):
	conf = []
	cnf = ConfigParser.RawConfigParser()
	path = getArduinoFile(confFile)
	if path is None: raise SystemExit(_("Cannot load %s file. Exiting.") % confFile)
	cnf.read(path)
	if not len(cnf.sections()):
		raise SystemExit(_("Error reading %s file. File is corrupt. Installation problem.\n") % path)
	c = 1
	for i in cnf.sections():
		v = dict(cnf.items(i))
		v['id'] = c
		v['desc'] = i
		conf.append(v)
		c = c + 1
	return conf

def makeWorkdir():
	return tempfile.mkdtemp("", os.path.join(tempfile.gettempdir(), "build"+str(time.time())))

def runProg(cmdline):
	sout = ""
	logging.debug("CMD:-%s", cmdline)
	try:
		p = subprocess.Popen(cmdline,
			stdout = subprocess.PIPE,
			stderr = subprocess.STDOUT,
			stdin = subprocess.PIPE,
			close_fds = True)
		poll = select.poll()
		poll.register(p.stdout, select.POLLIN)
		while gtk.events_pending():
			gtk.main_iteration()
		while True:
			o = p.stdout.readline()
			if o == '' and p.poll() != None: break
			while gtk.events_pending():
				gtk.main_iteration()
			sout += o
		if p.poll()==1: raise
	except OSError as e:
		err = "ERROR: Error running %s: %s" % (cmdline[0], e.strerror)
		return (False, err)
	except:
		logging.debug("ERR:%s", sout)
		return (False, sout)
	return (True, sout)

def runProgOutput(console, cmdline):
	sout = ""
	logging.debug("CMD:-%s", cmdline)
	try:
		p = subprocess.Popen(cmdline,
			stdout = subprocess.PIPE,
			stderr = subprocess.STDOUT,
			stdin = subprocess.PIPE,
			close_fds = True)
		poll = select.poll()
		poll.register(p.stdout, select.POLLIN)
		while gtk.events_pending():
			gtk.main_iteration()
		while True:
			o = p.stdout.readline()
			if o == '' and p.poll() != None: break
			pr = prefs.preferences()
			if pr.getBoolValue("build.verbose"):
				printMessageLn(console, o)
				sys.stderr.write(o)
			sout += o
		if p.poll()==1: raise
	except:
		logging.debug("ERR:%s", sout)
		return False
	return True

def get_mime_type(content):
	mime = Mime.get_type_by_data(content)
	"""try harder to guess mime type"""
	"""sometimes helps to trim leading newlines"""
	"""FIXME: try with smaller chunk of content"""
	if mime is None or mime == "text/plain":
		tmpmime = Mime.get_type_by_data(content.strip("\n"))
		if tmpmime and tmpmime != "text/plain": mime = tmpmime
		else: mime = "text/x-csrc"
	return str(mime)

def merge_font_name(widget, font):
	if widget == None: return
	context = widget.get_pango_context()
	font_desc = context.get_font_description()
	cur_font = pango.FontDescription(font)
	font_desc.merge(cur_font, True)
	return font_desc.to_string()

def getFontCharSize(widget):
	if widget == None: return
	context = widget.get_pango_context()
	font_desc = context.get_font_description()
	meter = context.get_metrics(font_desc)
	return meter.get_approximate_char_width()/1024

def set_widget_font(widget, font):
	if widget == None: return
	context = widget.get_pango_context()
	font_desc = context.get_font_description()
	cur_font = pango.FontDescription(font)
	font_desc.merge(cur_font, True)
	widget.modify_font(font_desc)

def setConsoleTags(console):
	b = console.get_buffer()
	tag = gtk.TextTag("red_foreground")
	tag.set_property("foreground", "red")
	table = b.get_tag_table()
	table.add(tag)
	tag = gtk.TextTag("white_foreground")
	tag.set_property("foreground", "white")
	table = b.get_tag_table()
	table.add(tag)

def clearConsole(console):
	b = console.get_buffer()
	b.delete(b.get_start_iter(), b.get_end_iter())
	b.set_text("")

def printError(notify, console, message):
	console.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color(red=1.0))
	b = console.get_buffer()
	if notify is not None:
		context = notify.get_context_id("main")
		notify.pop(context)
		notify.push(context, _("Error compiling."))
	b.delete(b.get_start_iter(), b.get_end_iter())
	b.set_text(message)

def printErrorLn(notify, console, error, message):
	b = console.get_buffer()
	if notify is not None:
		context = notify.get_context_id("main")
		notify.pop(context)
		notify.push(context, error)
	b.insert_with_tags_by_name(b.get_end_iter(), message, "red_foreground")
	b.place_cursor(b.get_end_iter())
	mark = b.get_insert()
	console.scroll_mark_onscreen(mark)

def printMessage(console, message):
	console.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color("#ffffff"))
	b = console.get_buffer()
	b.delete(b.get_start_iter(), b.get_end_iter())
	b.set_text(message)

def printMessageLn(console, message, verbose='false', wrap='true'):
	if message == '': return
	if wrap == 'true':
		rect =  console.get_allocation()
		width = rect.width/getFontCharSize(console)
		i=0
		m=''
		while i < len(message):
			m=m+message[i:i+width-3]+'\n'
			i+=width-3
	else: m=message
	if config.build_verbose == 'true' or verbose == 'true':
		console.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color("#ffffff"))
		b = console.get_buffer()
		b.insert(b.get_end_iter(), m)
		b.place_cursor(b.get_end_iter())
		mark = b.get_insert()
		console.scroll_mark_onscreen(mark)

def printLogMessageLn(message):
	if config.build_verbose == 'true': sys.stderr.write(message+"\n")

def statusMessage(w, text):
	w.push(1, text)
	glib.timeout_add(1000, lambda x: w.pop(1), 0)

def bufferModified(w, f):
	buf = hashlib.sha224(w.get_text(w.get_start_iter(), w.get_end_iter())).hexdigest()
	if f:
		fbuf = hashlib.sha224(file(f).read()).hexdigest()
	else:
		fbuf = hashlib.sha224("").hexdigest()
	if buf != fbuf: return True
	else: return False


def getBoards():
	res = []
	config = ConfigParser.RawConfigParser()
	config.read('BOARDS')
	for i in config.sections():
		res.append([i, config.get(i, 'size')])
	return res;

def createPopup(title, parent, msg):
	dialog = gtk.MessageDialog(parent,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_WARNING,
			gtk.BUTTONS_NONE,
			msg)
	dialog.add_buttons(_("Close without Saving"), 1, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			gtk.STOCK_SAVE, gtk.RESPONSE_YES)
	dialog.format_secondary_text(_("If you don't save, changes will be permanently lost."))
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	response = dialog.run()
	dialog.destroy()
	return response


def launch_in_browser(page):
	# The difficulty here is that the default open method for local files may not be
	# a browser (even with python webbrowser module). That's why we try first to read
	# the gconf key
	try:
		import gconf
		client = gconf.client_get_default()
		prog = client.get_string("/desktop/gnome/url-handlers/http/command")
		subprocess.Popen(prog % page, shell=True)
	except:
		gtk.show_uri(None, "file:///"+page, int(time.time()))

#float = config.getfloat('Section1', 'float')
#int = config.getint('Section1', 'int')
#print float + int
#	f = open("BOARDS")
#	for i in f:
#		print i.split(",")



# getfloat() raises an exception if the value is not a float
# getint() and getboolean() also do this for their respective types

# Notice that the next output does not interpolate '%(bar)s' or '%(baz)s'.
# This is because we are using a RawConfigParser().
#if config.getboolean('Section1', 'bool'):
#    print config.get('Section1', 'foo')


class MessageBox:

	def __init__(self):
		pass
	def show(self, message, message2):
		p = gtk.MessageDialog(None,
			gtk.DIALOG_MODAL,
			gtk.MESSAGE_INFO,
			gtk.BUTTONS_OK_CANCEL)
		p.set_markup(message)
		p.format_secondary_markup(message2)
		if p.run() == gtk.RESPONSE_OK:
			p.destroy()
			return True
		p.destroy()
		return False
