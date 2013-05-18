code:

		for i in range(2):
			print "a:", i

dis:

```
200           6 SETUP_LOOP              29 (to 38)
              9 LOAD_GLOBAL              1 (range)
             12 LOAD_CONST               1 (2)
             15 CALL_FUNCTION            1
             18 GET_ITER            
        >>   19 FOR_ITER                15 (to 37)
             22 STORE_FAST               1 (i)

201          25 LOAD_CONST               2 ('a:')
             28 PRINT_ITEM          
             29 LOAD_FAST                1 (i)
             32 PRINT_ITEM          
             33 PRINT_NEWLINE       
             34 JUMP_ABSOLUTE           19
        >>   37 POP_BLOCK           
```

We want to simulate `FOR_ITER`.

```
In [10]: def t(i):
   ....:     try:
   ....:         return next(i)
   ....:     except StopIteration:
   ....:         print "stop"
   ....:         

In [13]: dis.dis(t)
  2           0 SETUP_EXCEPT            14 (to 17)

  3           3 LOAD_GLOBAL              0 (next)
              6 LOAD_FAST                0 (i)
              9 CALL_FUNCTION            1
             12 RETURN_VALUE        
             13 POP_BLOCK           
             14 JUMP_FORWARD            22 (to 39)

  4     >>   17 DUP_TOP             
             18 LOAD_GLOBAL              1 (StopIteration)
             21 COMPARE_OP              10 (exception match)
             24 POP_JUMP_IF_FALSE       38
             27 POP_TOP             
             28 POP_TOP             
             29 POP_TOP             

  5          30 LOAD_CONST               1 ('stop')
             33 PRINT_ITEM          
             34 PRINT_NEWLINE       
             35 JUMP_FORWARD             1 (to 39)
        >>   38 END_FINALLY         
        >>   39 LOAD_CONST               0 (None)
             42 RETURN_VALUE        
```
