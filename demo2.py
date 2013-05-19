# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.


import sys
import dis
from FuncModify import *
from utils import *


def demo2():
	# Let the user create some Python code.
	import os, tempfile
	editcmd = os.environ.get("EDITOR", "vi")
	tmpfn = tempfile.mktemp(suffix=".py")
	open(tmpfn, "w").write(
		"def main():\n"
		"	# Write some code here.\n"
		"	# When done, safe and exit. This code will get executed then.\n"
		"	# You can raise an exception via code here.\n"
		"	# Or just write an infinite loop and press Ctrl+C at execution.\n"
		"	import time\n"
		"	i = 0\n"
		"	while True:\n"
		"		i += 1\n"
		"		print i\n"
		"		time.sleep(1)\n"
		"\n"
	)
	os.system("%r %r" % (editcmd, tmpfn))

	# Make a backup of the file.
	tmpbackupfn = tempfile.mktemp(suffix=".py")
	os.system("cp %r %r" % (tmpfn, tmpbackupfn))

	# Now run the code.
	import imp
	tmpfnmod = imp.load_source("tmpfnmod", tmpfn)
	func = tmpfnmod.main
	try:
		func()
		assert False, "You must raise an exception for this demo."
	except BaseException:
		import sys
		excinfo = sys.exc_info()
		sys.excepthook(*excinfo)
		tb = excinfo[-1]
	tb = _find_traceframe(tb, func.func_code)
	assert tb is not None
	localdict = dict(tb.tb_frame.f_locals)

	# Write hint about exception.
	lines = list(open(tmpfn).readlines())
	lineno = tb.tb_lineno - 1
	lines[lineno:lineno] = [
		"# The exception was raised in the following line!\n",
		"# Now modify it as you wish. :)\n"
	]
	open(tmpfn, "w").writelines(lines)

	# Let the user edit the file again.
	os.system("%r %r" % (editcmd, tmpfn))

	# Reload file.
	tmpfnmod = imp.load_source("tmpfnmod", tmpfn)
	func = tmpfnmod.main
	# Calculate new line number.
	newlineno = _calc_newlineno_via_diff(tb.tb_lineno, tmpbackupfn, tmpfn)
	print "Restarting in line %i at %r" % (newlineno, open(tmpfn).readlines()[newlineno-1].strip())
	# Use that instruction address.
	instraddr = min([addr for (addr,lineno) in dis.findlinestarts(func.func_code) if lineno >= newlineno])

	# Register some cleanup handlers.
	import atexit
	atexit.register(lambda: os.remove(tmpfn))
	atexit.register(lambda: os.remove(tmpbackupfn))

	# Now, do the magic!
	# Create a modified function which jumps right to the previous place.
	newfunc = restart_func(func, instraddr=instraddr, localdict=localdict)
	# And run it.
	newfunc()

	# Note that we could have also pickled the localdict to disk and restart
	# the updated function later on in a new Python instance.


if __name__ == "__main__":
	demo2()
