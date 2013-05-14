
import dis
from FuncModify import restart_func

def _find_traceframe(tb, code):
	while tb:
		if tb.tb_frame.f_code is code: return tb
		tb = tb.tb_next
	return None

def demo1():
	def demoFunc(a,b,c, raiseExc=None):
		print("a: %r" % a)
		while b > 0:
			print("b: %r" % b)
			if b == 4 and raiseExc: raise raiseExc
			if b == 2:
				b = 0
				continue
			b -= 1
		print("c: %r" % c)

	func = demoFunc
	try:
		# This prints:
		#   a: 'start'
		#   b: 5
		# And throws the exception then.
		demoFunc("start", 5, "end", Exception)
		assert False
	except Exception:
		print "! Exception"
		import sys
		_,_,tb = sys.exc_info()

	tb = _find_traceframe(tb, func.func_code)
	assert tb is not None

	# Start just one after the `raise`.
	instraddr = min([addr for (addr,_) in dis.findlinestarts(func.func_code) if addr > tb.tb_lasti])
	# Play around. Avoid that we throw the exception again.
	localdict = dict(tb.tb_frame.f_locals)
	localdict["b"] = 5
	localdict["raiseExc"] = None
	new_func = restart_func(func, instraddr=instraddr, localdict=localdict)

	# This prints:
	#   b: 4
	#   b: 3
	#   b: 2
	#   c: 'end'
	new_func()


if __name__ == "__main__":
	demo1()
