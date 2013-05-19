# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.

# Some tests with `simplify_loops` and `add_debug_prints_after_stores`.

import dis
from FuncModify import *


def demo5():
	def func():
		print "foo"
		for i in range(2):
			print i, "bar"
		print "baz"
	def func_simplified():
		print "foo"
		__loopiter_1 = iter(range(2))
		while True:
			try:
				i = next(__loopiter_1)
			except StopIteration:
				break
			print i, "bar"
		print "baz"
	print "normal:"
	dis.dis(func)
	func()
	print "simplified:"
	dis.dis(func_simplified)
	func_simplified()
	print "auto simplified:"
	func_autosimple = simplify_loops(func)
	dis.dis(func_autosimple)
	func_autosimple()
	print "debug:"
	func_debug = add_debug_prints_after_stores(func_autosimple)
	dis.dis(func_debug)
	func_debug()
	return func_debug


if __name__ == "__main__":
	demo5()
