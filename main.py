

import dis
import types


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

def _codestr_without_final_return(codestr):
	assert len(codestr) >= 4
	assert codestr[-4] == dis.opmap["LOAD_CONST"]
	assert codestr[-1] == dis.opmap["RETURN_VALUE"]
	return codestr[:-4]

def _join_codestr(codestr1, codestr2, firstlineno2, lnotab2):
	# see dis.findlinestarts() about co_firstlineno and co_lnotab
	codestr1 = _codestr_without_final_return(codestr1)
	codestr = codestr1 + codestr2
	_modify_abs_jumps(codestr, start=len(codestr1), end=len(codestr), jumprel=len(codestr1))
	return codestr

def _modify_code(c, codestr):

	CodeArgs = [
		"argcount", "nlocals", "stacksize", "flags", "code",
		"consts", "names", "varnames", "filename", "name",
		"firstlineno", "lnotab", "freevars", "cellvars"]
	c_dict = dict([(arg, getattr(c, "co_" + arg)) for arg in CodeArgs])
	c_dict["code"] = codestr

	c = types.CodeType(*[c_dict[arg] for arg in CodeArgs])
	return c

def _merge_locals(localdict):
	#locals().update(localdict)
	a = 42

def restart_func(func, instraddr, localdict):
	preload_code = ""
	code_consts = func.func_code.co_consts
	LOAD_CONST = chr(dis.opmap["LOAD_CONST"])
	for key,value in localdict.items():
		co_const_idx = len(code_consts)
		code_consts += (value,)
		preload_code += LOAD_CONST
		preload_code += chr(co_const_idx & 255) + chr(co_const_idx >> 8)
	instraddr += len(preload_code) + 3 # 3 for the following jump_abs
	preload_code += chr(dis.opmap["JUMP_ABSOLUTE"])
	
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

def demoFunc(a,b,c, raiseExc=None):
	print("a: %r" % a)
	while b:
		print("b: %r" % b)
		if b == 3 and raiseExc: raise raiseExc
		b -= 1
	print("c: %r" % c)

def _find_traceframe(tb, code):
	while tb:
		if tb.tb_frame.f_code is code: return tb
		tb = tb.tb_next
	return None

def demo():
	try:
		demoFunc(5,4,1, Exception)
	except Exception:
		import sys
		_,_,tb = sys.exc_info()
		tb = _find_traceframe(tb, demoFunc.func_code)
		localdict = tb.tb_frame.f_locals
		lineno = tb.tb_lineno #, tb.tb_frame.f_lineno
		instaddr = tb.tb_lasti # tb.tb_frame.f_lasti

	localdict["b"] = 2
