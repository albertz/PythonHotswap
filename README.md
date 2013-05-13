Python Hotswap
==============

Hotswap Python functions. And persistence of runtime.

Originally, the idea was to write a simple Python bytecode interpreter and run Python bytecode in Python. Then, this could be used to save all the state (via pickling) and then later recover at some arbitrary position in the bytecode.

Via some clever diffing algorithm, it would be determined from the old bytecode compared to the new bytecode where to restart.

Another idea to avoid the implementation of a bytecode interpreter is to wrap the original bytecode and in the patched wrapped version, it starts by recovering the state (local variables) and then jumps right to the wanted position.

The problem of getting the exact state could be solved via exceptions to get the frame info.

