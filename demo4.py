# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.

# Same as `demo3` but with `for`-loops.

import sys
import dis
from FuncModify import *
from utils import *


def demo4():
	def func():
		bug = True
		for i in range(3):
			print "a:", i
		for i in range(3):
			print "b:", i
			if bug: raise Exception

	func = simplify_loops(func)

	try:
		func()
		assert False
	except Exception:
		print "! Exception"
		_,_,tb = sys.exc_info()

	tb = _find_traceframe(tb, func.func_code)
	assert tb is not None

	# Start just at where the exception was raised.
	instraddr = max([addr for (addr,_) in dis.findlinestarts(func.func_code) if addr <= tb.tb_lasti])
	# Play around. Avoid that we throw the exception again.
	localdict = dict(tb.tb_frame.f_locals)
	localdict["bug"] = False
	new_func = restart_func(func, instraddr=instraddr, localdict=localdict)

	new_func()


if __name__ == "__main__":
	demo4()

