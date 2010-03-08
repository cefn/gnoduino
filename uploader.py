
import misc
import time

avr = [
	"hardware/tools/avrdude",
	"-Chardware/tools/avrdude.conf",
	"-v",
	"-v",
	"-v",
	"-v",
	"-pm8",
	"-cstk500v1",
	"-P/dev/ttyS0",
	"-b19200",
	"-D"
]

def upload(obj, serial, output, notify):
	serial.resetBoard()
	compline=[i for i in avr]
	compline.append("-Uflash:w:"+obj+".hex:i")
	print compline
	(run, sout) = misc.runProg(compline)
	print sout
	if run == False:
		misc.printError(notify, output, sout)
		raise

