# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.

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

def _find_setup_blocks(codestr):
	"Yields (op, absolute target instraddr)"
	end = len(codestr)
	i = 0
	SETUPS = [dis.opmap[opname] for opname in ["SETUP_LOOP", "SETUP_EXCEPT", "SETUP_FINALLY"]]
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

		if op in SETUPS:
			assert op >= dis.HAVE_ARGUMENT
			yield (op, i + num)

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

	setup_blocks = list(_find_setup_blocks(func.func_code.co_code))
	preload_code_len = len(localdict) * 6 + len(setup_blocks) * 3 + 3
	for op,targetaddr in setup_blocks:
		targetaddr += preload_code_len
		reladdr = targetaddr - (len(preload_code) + 3)
		preload_code += chr(op) + chr(reladdr & 255) + chr(reladdr >> 8)

	instraddr += preload_code_len
	preload_code += chr(dis.opmap["JUMP_ABSOLUTE"])
	preload_code += chr(instraddr & 255) + chr(instraddr >> 8)

	# Just a check. LoadConst+StoreFast, then .. and then JumpAbs.
	assert preload_code_len == len(preload_code)

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
