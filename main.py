

import dis

def _modify_abs_jumps(codestr, start, end, jumprel):
	i = start
	while i < end:
		op = ord(codestr[i])
		i += 1

		if op >= dis.HAVE_ARGUMENT:
			b1 = ord(codestr[i])
			b2 = ord(codestr[i+1])
			num = b2 * 256 + b1
			del b1,b2
			i += 2
		else:
			num = 0

		if op in dis.hasjabs:
			assert op >= dis.HAVE_ARGUMENT
			num += jumprel
			codestr[i-2] = chr(num & 255)
			codestr[i-1] = chr(num >> 8)

def _join_codestr(codestr1, codestr2):
	# see dis.findlinestarts() about co_firstlineno and co_lnotab
	codestr = codestr1 + codestr2
	_modify_abs_jumps(codestr, start=len(codestr1), end=len(codestr), jumprel=len(codestr1))
	return codestr

def restart_func(func, codeline, localdict):

	end = len(func.func_code.co_code)
	i = 0
	while i < end:
		op = ord(func.func_code.co_code[i])
		i += 1
		name = dis.opname[op]

		if op >= dis.HAVE_ARGUMENT:
			b1 = ord(func.func_code.co_code[i])
			b2 = ord(func.func_code.co_code[i+1])
			num = b2 * 256 + b1
			del b1,b2
			i += 2
		else:
			num = 0

		if op in dis.hasjabs:
			print dis.opname[op] + " to " + repr(num)

