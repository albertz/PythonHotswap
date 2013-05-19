# Copyright (c) 2013, Albert Zeyer, www.az2000.de
# All rights reserved.
# Code under 2-clause BSD licence.

import dis
import types

def _modified_jumps(codestr, jumprel=None, jumpaddrmap=None, start=None, end=None):
	if jumprel is not None:
		assert jumpaddrmap is None, "specify only one of jumprel and jumpaddrmap"
		jumpaddrmap = lambda n: n + jumprel
	assert jumpaddrmap is not None, "one of jumprel and jumpaddrmap must be specified"

	codestr = bytearray(codestr)
	if start is None: start = 0
	if end is None: end = len(codestr)
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
			num = jumpaddrmap(num)
			codestr[i-2] = chr(num & 255)
			codestr[i-1] = chr(num >> 8)

		if op in dis.hasjrel and jumprel is None:
			assert op >= dis.HAVE_ARGUMENT
			num += i # because it is a relative jump
			num = jumpaddrmap(num) # map
			num -= i # convert back to relative jump
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
	codestr = _modified_jumps(codestr, start=len(codestr1), end=len(codestr), jumprel=len(codestr1))
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


def replace_code(codeobj, instaddr, removelen=0, addcodestr=""):
	assert isinstance(codeobj, types.CodeType)
	assert removelen >= 0
	if removelen == 0 and len(addcodestr) == 0: return codeobj

	# Search right place in lnotab.
	lnotab = codeobj.co_lnotab
	assert len(lnotab) % 2 == 0
	lnotab_instaddr = 0
	lnotab_idx = 0
	lnotab_len = len(lnotab)
	while lnotab_idx < lnotab_len:
		if lnotab_instaddr >= instaddr: break
		addrincr, lineincr = map(ord, lnotab[lnotab_idx:lnotab_idx+2])
		lnotab_instaddr += addrincr
		lnotab_idx += 2
	assert lnotab_instaddr >= instaddr, "instaddr %i not in lnotab" % instaddr

	# If we skipped it, insert a dummy entry to lnotab.
	if lnotab_instaddr > instaddr:
		# Insert. addrincr, lineincr are from the last entry.
		lnotab = \
			lnotab[:lnotab_idx-2] + \
			chr(addrincr - (lnotab_instaddr - instaddr)) + chr(0) + \
			chr(lnotab_instaddr - instaddr) + chr(lineincr) + \
			lnotab[lnotab_idx:]
		lnotab_idx -= 2
		lnotab_instaddr = instaddr
	del addrincr, lineincr
	assert lnotab_instaddr == instaddr
	# And lnotab_idx is right where the upcoming lnotab-data starts.

	# Check whether instaddr is sane.
	codestr = codeobj.co_code
	codeidx = 0
	codelen = len(codestr)
	while codeidx < codelen:
		if codeidx >= instaddr: break
		op = ord(codestr[codeidx])
		codeidx += 1
		if op >= dis.HAVE_ARGUMENT: codeidx += 2
	assert codeidx == instaddr, "instaddr %i doesn't align in code" % instaddr

	# Check whether removelen is sane.
	while codeidx < codelen:
		if codeidx >= instaddr + removelen: break
		op = ord(codestr[codeidx])
		codeidx += 1
		if op >= dis.HAVE_ARGUMENT: codeidx += 2
	assert codeidx == instaddr + removelen, "removelen %i doesn't align in code" % removelen

	# Update lnotab for removed code.
	while lnotab_idx < lnotab_len:
		if lnotab_instaddr >= instaddr + removelen: break
		addrincr, lineincr = map(ord, lnotab[lnotab_idx:lnotab_idx+2])
		lnotab_instaddr += addrincr
		lnotab_idx += 2
	assert lnotab_instaddr >= instaddr + removelen, "lnotab is invalid"

	# If we skipped it, insert a dummy entry to lnotab.
	if lnotab_instaddr > instaddr + removelen:
		# Insert. addrincr, lineincr are from the last entry.
		lnotab = \
			lnotab[:lnotab_idx-2] + \
			chr(addrincr - (lnotab_instaddr - (instaddr + removelen))) + chr(0) + \
			chr(lnotab_instaddr - (instaddr + removelen)) + chr(lineincr) + \
			lnotab[lnotab_idx:]
		lnotab_idx -= 2
		lnotab_instaddr = instaddr + removelen
	assert lnotab_instaddr == instaddr + removelen

	# Update lnotab for new code.
	codelendiff = len(addcodestr)
	while codelendiff > 0:
		lnotab = \
			lnotab[:lnotab_idx] + \
			chr(codelendiff & 255) + chr(0) + \
			lnotab[lnotab_idx:]
		codelendiff -= codelendiff & 255
	assert codelendiff == 0
	del codelendiff

	# Check whether addcodestr is sane.
	codeidx = 0
	codelen = len(addcodestr)
	while codeidx < codelen:
		op = ord(addcodestr[codeidx])
		codeidx += 1
		if op >= dis.HAVE_ARGUMENT: codeidx += 2
	assert codeidx == codelen, "addcodestr is not sane. %r" % ((codeidx, codelen),)

	# Update absolute jumps in code start.
	def codestr_jumpaddrmap(n):
		if n <= instaddr: return n
		if n >= instaddr + removelen: return n - removelen + len(addcodestr)
		assert False, "invalid jump %i in code" % n
	codestr_start = _modified_jumps(
		codestr[:instaddr],
		jumpaddrmap=codestr_jumpaddrmap)

	# Update absolute jumps in code end.
	codestr_end = _modified_jumps(
		codestr[instaddr+removelen:],
		jumpaddrmap=codestr_jumpaddrmap)

	# Update codestr.
	codestr = codestr_start + addcodestr + codestr_end

	# Return new code object.
	new_code = _modified_code(
		codeobj,
		code=codestr,
		lnotab=lnotab,
	)
	return new_code


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


def _get_varnameprefix_startidx(varnames, varnameprefix, start=1, incr=1):
	varnameprefix += "_"
	relidx = len(varnameprefix)
	varnames = [name[relidx:] for name in varnames if name.startswith(varnameprefix)]
	def map_postfix(s):
		try: return int(s)
		except ValueError: return -1
	varnames = map(map_postfix, varnames)
	varnames.sort()
	if len(varnames) == 0:
		return start
	return varnames[-1] + incr


def _opiter(codestr):
	i = 0
	codelen = len(codestr)
	while i < codelen:
		codeaddr = i
		op = ord(codestr[i])
		i += 1

		if op >= dis.HAVE_ARGUMENT:
			b1,b2 = map(ord, codestr[i:i+2])
			arg = b2 * 256 + b1
			del b1,b2
			i += 2
		else:
			arg = None

		yield (codeaddr, op, arg)


def _codeops_compile(codeops):
	codestr = ""
	for op,arg in codeops:
		if isinstance(op, str):
			op = dis.opmap[op]
		codestr += chr(op)
		if op >= dis.HAVE_ARGUMENT:
			assert arg is not None
			assert arg >= 0 and arg < 256 * 256
			codestr += chr(arg & 255) + chr(arg >> 8)
		else:
			assert arg is None
	return codestr


def _list_getobjoradd(consts, obj, equalop=lambda a,b: a is b):
	for i in range(len(consts)):
		if equalop(consts[i], obj):
			return consts, i
	return consts + (obj,), len(consts)

def simplify_loops(func):
	"""
	Returns a new modified version of `func` which behaves exactly the same but
	which has all for-loops replaced with while-loops. This makes it compatible
	for `restart_func`.
	"""

	codeobj = func.func_code

	names = func.func_code.co_names
	names, names_next_idx = _list_getobjoradd(names, "next")
	names, names_StopIter_idx = _list_getobjoradd(names, "StopIteration")
	codeobj = _modified_code(
		codeobj,
		names=names,
	)

	varnames = func.func_code.co_varnames
	varidx = _get_varnameprefix_startidx(varnames, "__loopiter")

	oplist = list(_opiter(codeobj.co_code))
	codeaddrdiff = 0
	for i in range(len(oplist)):
		codeaddr, op, arg = oplist[i]
		codeaddr += codeaddrdiff

		if op == dis.opmap["FOR_ITER"]:
			# Get a new unique variable name for the iterator object.
			varnameidx = len(varnames)
			varnames += ("__loopiter_%i" % varidx,)
			varidx += 1
			codeobj = _modified_code(
				codeobj,
				varnames=varnames,
			)

			# We expect that the loop jumps back to the FOR_ITER and thus expects
			# to have one item (the iter) on the stack. We don't want that for
			# simple code resuming (via `restart_func`) because it is not what we have
			# in a simple `while` loop.
			# Thus, right in front of the FOR_ITER, insert the STORE_FAST for the iter.

			# The way `replace_code` works, we need to replace the previous op because
			# we want that jumps to the FOR_ITER keeps pointing there.
			assert i > 0
			codestr = _codeops_compile([
				(oplist[i-1][1], oplist[i-1][2]),
				("STORE_FAST", varnameidx)
			])
			codeobj = replace_code(
				codeobj,
				instaddr=oplist[i-1][0] + codeaddrdiff, # at the last op
				removelen=oplist[i][0] - oplist[i-1][0], # just the last op
				addcodestr=codestr)
			codeaddrdiff += 3 # the STORE_FAST
			codeaddr += 3

			# debug
			codeobj = replace_code(
				codeobj,
				instaddr=codeaddr,
				removelen=0,
				addcodestr=_codeops_compile([
					("LOAD_FAST", varnameidx),
					("PRINT_ITEM", None),
					("PRINT_NEWLINE", None),
				]))
			codeaddrdiff += 5
			codeaddr += 5
			# debug end

			forIterAddr = codeaddr
			forIterAbsJumpTarget = codeaddr + 3 + arg

			# We expect the next op to be STORE_FAST, where we store the result of `next(iter)`.
			assert i < len(oplist) - 1 and oplist[i+1][1] == dis.opmap["STORE_FAST"]
			nextvar_varnameidx = oplist[i+1][2]

			# Now call `next()` on it and catch StopIteration.
			# Note that all jump-constants here are carefully adjusted.
			# If you change something here, probably all of them need to be updated!
			codeops = [
				("SETUP_EXCEPT", 16), # in case of exception, jump to DUP_TOP
				("LOAD_GLOBAL", names_next_idx),
				("LOAD_FAST", varnameidx),
				("CALL_FUNCTION", 1),
				("STORE_FAST", nextvar_varnameidx),
				("POP_BLOCK", None),
				("JUMP_FORWARD", 17), # jump outside of `try/except`, one after END_FINALLY
				("DUP_TOP", None),
				("LOAD_GLOBAL", names_StopIter_idx),
				("COMPARE_OP", 10), # exception match
				("POP_JUMP_IF_FALSE", 35 + forIterAddr), # jump to END_FINALLY
				("POP_TOP", None),
				("POP_TOP", None),
				("POP_TOP", None),
				("JUMP_ABSOLUTE", forIterAbsJumpTarget + 30), # the FOR_ITER target (adjusted with diff)
				("END_FINALLY", None),
			]

			codestr = _codeops_compile(codeops)
			removelen = 6 # FOR_ITER and STORE_FAST
			codeaddrdiff += len(codestr) - removelen
			codeobj = replace_code(codeobj, instaddr=codeaddr, removelen=removelen, addcodestr=codestr)

	new_func = types.FunctionType(
		codeobj,
		func.func_globals,
		func.func_name,
		func.func_defaults,
		func.func_closure,
	)
	return new_func


def add_debug_prints_after_stores(func):
	"""
	Returns a new modified version of `func` which prints
	every value after a STORE_FAST.
	"""

	codeobj = func.func_code

	consts = codeobj.co_consts
	varnameindexes = [None] * len(codeobj.co_varnames)
	for i in range(len(varnameindexes)):
		consts, varnameindexes[i] = _list_getobjoradd(consts, codeobj.co_varnames[i], lambda a,b: a == b)
	consts, equalstridx = _list_getobjoradd(consts, "=", lambda a,b: a == b)
	codeobj = _modified_code(
		codeobj,
		consts=consts,
	)

	oplist = list(_opiter(codeobj.co_code))
	codeaddrdiff = 0
	for i in range(len(oplist)):
		codeaddr, op, arg = oplist[i]
		codeaddr += codeaddrdiff

		if op == dis.opmap["STORE_FAST"]:
			varidx = arg
			assert 0 <= varidx < len(varnameindexes)
			addcodestr = _codeops_compile([
				("LOAD_CONST", varnameindexes[varidx]),
				("PRINT_ITEM", None),
				("LOAD_CONST", equalstridx),
				("PRINT_ITEM", None),
				("LOAD_FAST", varidx), # load the same var
				("PRINT_ITEM", None),
				("PRINT_NEWLINE", None)
			])
			codeobj = replace_code(
				codeobj,
				instaddr=codeaddr+3, # right after the STORE_FAST
				removelen=0,
				addcodestr=addcodestr
			)
			codeaddrdiff += len(addcodestr)


	new_func = types.FunctionType(
		codeobj,
		func.func_globals,
		func.func_name,
		func.func_defaults,
		func.func_closure,
	)
	return new_func
