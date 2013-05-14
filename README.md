# Python Hotswap

Hotswap Python functions. And persistence of runtime.

## The problem I'm trying to solve:

You have a complicated function which calculates something (some physics simulation or mathematical data or so) and takes some long time (hours, days). It consists of one or more loops.

You find a small mistake while it is running which can easily be solved and it wouldn't really be needed to restart from the beginning. Maybe an unhandled exception occured.

You want to edit the code, maybe modify some local variables and just resume the execution where it was.

## This project.

Solves this problem! :)

Take a look at `demo2()` in [main.py](https://github.com/albertz/PythonHotswap/blob/master/main.py). It lets the user edit some simple function, then runs it and waits for an exception. Or just press Ctrl+C to break it. Then it lets the user edit the function again with a hint where the exception occured. After the edit, it resumes the execution at the place where the exception occured. Via the `diff` tool, it determines the new line number.

Start it via `python main.py demo2` to play around with it.

## How to solve that.

Originally, the idea was to write a simple Python bytecode interpreter and run Python bytecode in Python. Then, this could be used to save all the state (via pickling) and then later recover at some arbitrary position in the bytecode.

Via some clever diffing algorithm, it would be determined from the old bytecode compared to the new bytecode where to restart.

Another idea to avoid the implementation of a bytecode interpreter is to wrap the original bytecode and in the patched wrapped version, it starts by recovering the state (local variables) and then jumps right to the wanted position.

The problem of getting the exact state could be solved via exceptions to get the frame info.

This is how it is solved now. See [FuncModify.py](https://github.com/albertz/PythonHotswap/blob/master/FuncModify.py) for details.

The bootstrap code to setup the Python execution frame does the following:

- Recover the local dict.
- Setup execution blocks (like loops).
- Jump to the resume opcode address.

That's it for now. - [Albert Zeyer](mailto:albzey@gmail.com)
