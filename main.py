

import dis, opcode

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

		if op in opcode.hasjabs:
			print opcode.opname[op] + " to " + repr(num)

