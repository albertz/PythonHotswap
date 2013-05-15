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

def _find_setup_blocks(codestr, start, end):
	"Yields (op, absolute target instraddr, loop-type)"
	i = start
	SETUPS = [dis.opmap[opname] for opname in ["SETUP_LOOP", "SETUP_EXCEPT", "SETUP_FINALLY"]]
	POP_BLOCK = dis.opmap["POP_BLOCK"]
	FOR_ITER = dis.opmap["FOR_ITER"]
	blockstack = []
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
			blockstack += [[op, i + num, None]]

		elif op == FOR_ITER:
			assert len(blockstack) > 0
			blockstack[-1][2] = op

		elif op == POP_BLOCK:
			assert len(blockstack) > 0
			blockstack.pop(len(blockstack) - 1)

	return blockstack

def restart_func(func, instraddr, localdict):
	"""
	Returns a new modified version of `func` which jumps right to instraddr
	with the localdict in place.

	Note that the way this currently works is limited because it uses
	only standard Python functions and objects. Only while-loops are supported.

	For-loops are not supported and are not possible this way.
	Except-blocks and with-blocks are not tested and will probably crash.
	"""

	# Another possibility to do this:
	# We need ctypes. Then we just save the full stack and the current op.
	# We can just load the full stack via LOAD_CONST.
	# This again has some problems such as that we don't want to resume
	# right at the op (because that might be the one raising an exception).
	# And if you want to resume somewhere else, you again need to manually
	# recalculate the stack so that it stays same.

	# And yet another:
	# We could also return a modified version of the func which automatically
	# replaces all for-loops with while-loops and store the iterator object
	# in a temporary local variable. However, still left is the problem that
	# many iterator objects (e.g. listiterator) are not pickable, so
	# serializing doesn't work. This again could be hacked via ctypes.

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

	setup_blocks = _find_setup_blocks(func.func_code.co_code, start=0, end=instraddr)
	preload_code_len = len(localdict) * 6 + len(setup_blocks) * 3 + 3
	for op,targetaddr,looptype in setup_blocks:
		# Note on the loop-type:
		# Supporting for-loops is really complicated! We need to examine the stack of
		# the frame to get the iterator object. This cannot be done with the
		# normal Python APIs - we need ctypes to get raw access to PyFrameObject.
		# Then, even more complicated is to get the right stack address. You
		# have to go back from the opaddr where you are to the last FOR_ITER and count
		# the stack modifications.
		# Then, if you raise an exception and catch it outside, you already have lost
		# the stack and thus the iterator object - so this is not an option.
		# You need to do this while it is still active - e.g. from within an
		# exception trace function.
		assert looptype is None, "only while-loops supported at the moment"
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

def simplify_loops(func):
	"""
	Returns a new modified version of `func` which behaves exactly the same but
	which has all for-loops replaced with while-loops. This makes it compatible
	for `restart_func`.
	"""

	codestr = list(map(ord, func.func_code.co_code))
	opaddrmap = dict(zip(range(len(codestr)), range(len(codestr))))

	# TODO: search for FOR_ITER, etc...

	# TODO: fix up lnotab.
	lnotab = ""

	# Fix up the absolute jumps.
	i = 0
	while i < len(codestr):
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
			num = opaddrmap[num]
			codestr[i-2] = chr(num & 255)
			codestr[i-1] = chr(num >> 8)

	new_code = _modified_code(
		func.func_code,
		code="".join(map(chr, codestr)),
		lnotab=lnotab,
	)
	new_func = types.FunctionType(
		new_code,
		func.func_globals,
		func.func_name,
		func.func_defaults,
		func.func_closure,
	)
	return new_func
