

import dis
import types


def _modified_abs_jumps(codestr, start, end, jumprel):
	codestr = bytearray(codestr)
	i = start
	while i < end:
		op = codestr[i]
		i += 1

		if op >= dis.HAVE_ARGUMENT:
			b1 = codestr[i]
			b2 = codestr[i+1]
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

	return str(codestr)

def _codestr_without_final_return(codestr):
	assert len(codestr) >= 4
	assert codestr[-4] == dis.opmap["LOAD_CONST"]
	assert codestr[-1] == dis.opmap["RETURN_VALUE"]
	return codestr[:-4]

def _prefix_codestr(codestr1, codestr2):
	# see dis.findlinestarts() about co_firstlineno and co_lnotab
	codestr = codestr1 + codestr2
	codestr = _modified_abs_jumps(codestr, start=len(codestr1), end=len(codestr), jumprel=len(codestr1))
	return codestr

def _modified_code(c, **kwargs):
	CodeArgs = [
		"argcount", "nlocals", "stacksize", "flags", "code",
		"consts", "names", "varnames", "filename", "name",
		"firstlineno", "lnotab", "freevars", "cellvars"]
	c_dict = dict([(arg, getattr(c, "co_" + arg)) for arg in CodeArgs])

	for key,value in kwargs.items():
		assert key in c_dict
		c_dict[key] = value

	c = types.CodeType(*[c_dict[arg] for arg in CodeArgs])
	return c

def restart_func(func, instraddr, localdict):
	preload_code = ""
	code_consts = func.func_code.co_consts
	LOAD_CONST = chr(dis.opmap["LOAD_CONST"])
	STORE_FAST = chr(dis.opmap["STORE_FAST"])
	for key,value in localdict.items():
		co_const_idx = len(code_consts)
		code_consts += (value,)
		preload_code += LOAD_CONST + chr(co_const_idx & 255) + chr(co_const_idx >> 8)
		varidx = func.func_code.co_varnames.index(key)
		preload_code += STORE_FAST + chr(varidx & 255) + chr(varidx >> 8)
	instraddr += len(preload_code) + 3 # 3 for the following jump_abs
	preload_code += chr(dis.opmap["JUMP_ABSOLUTE"])
	preload_code += chr(instraddr & 255) + chr(instraddr >> 8)

	codestr = _prefix_codestr(preload_code, func.func_code.co_code)

	lnotab = func.func_code.co_lnotab
	lnotab_moverel = len(preload_code)
	while lnotab_moverel > 0:
		lnotab = chr(lnotab_moverel & 255) + chr(0) + lnotab
		lnotab_moverel -= lnotab_moverel & 255

	new_code = _modified_code(
		func.func_code,
		consts=code_consts,
		code=codestr,
		lnotab=lnotab,
		argcount=0
	)
	new_func = types.FunctionType(
		new_code,
		func.func_globals,
		func.func_name,
		func.func_defaults,
		func.func_closure,
	)
	return new_func

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
	func = demoFunc
	try:
		demoFunc(5,4,1, Exception)
		assert False
	except Exception:
		import sys
		_,_,tb = sys.exc_info()

	tb = _find_traceframe(tb, func.func_code)
	assert tb is not None
	localdict = tb.tb_frame.f_locals
	lineno = tb.tb_lineno #, tb.tb_frame.f_lineno
	instraddr = tb.tb_lasti # tb.tb_frame.f_lasti

	instraddr += 3 if ord(func.func_code.co_code[instraddr]) >= dis.HAVE_ARGUMENT else 1
	localdict["b"] = 2
	new_func = restart_func(func, instraddr=instraddr, localdict=localdict)

	return new_func

if __name__ == "__main__":
	f = demo()
	f()
