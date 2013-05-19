# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.


def _find_traceframe(tb, code):
	while tb:
		if tb.tb_frame.f_code is code: return tb
		tb = tb.tb_next
	return None


def _calc_newlineno_via_diff(oldlineno, oldfilename, newfilename):
	from subprocess import Popen, PIPE
	diffcmd = ["diff", "-EbwB", "-U", "0"]
	diffout = Popen(diffcmd + [oldfilename, newfilename], stdout=PIPE).stdout.readlines()
	lineno = 1
	newlineno = 1
	import re
	r = re.compile(r"^@@ -([0-9]+).*@@.*$")
	for diffline in diffout:
		if diffline.startswith("--- "): continue
		if diffline.startswith("+++ "): continue
		m = r.match(diffline)
		if m:
			nextlineno = int(m.groups()[0])
			if nextlineno > oldlineno:
				return newlineno + (oldlineno - lineno)
			newlineno += (nextlineno - lineno)
			lineno = nextlineno
			continue
		assert diffline[0:1] in "+-" # because of "diff -U 0"
		if diffline[0] == "+":
			newlineno += 1
		elif diffline[0] == "-":
			lineno += 1
		if lineno > oldlineno:
			return newlineno
	return newlineno + (oldlineno - lineno)
