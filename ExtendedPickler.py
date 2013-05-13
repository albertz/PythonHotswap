# Code by Albert Zeyer.
# Code under 2-clause BSD licence.

import pickle, types, marshal, sys
CellType = type((lambda x: lambda: x)(0).func_closure[0])
def makeCell(value): return (lambda: value).func_closure[0]
def getModuleDict(modname): return __import__(modname).__dict__
class Pickler(pickle.Pickler):
	def __init__(self, *args, **kwargs):
		if not "protocol" in kwargs:
			kwargs["protocol"] = pickle.HIGHEST_PROTOCOL
		pickle.Pickler.__init__(self, *args, **kwargs)
	dispatch = pickle.Pickler.dispatch.copy()

	def save_func(self, obj):
		try:
			self.save_global(obj)
			return
		except pickle.PicklingError:
			pass
		assert type(obj) is types.FunctionType
		self.save(types.FunctionType)
		self.save((
			obj.func_code,
			obj.func_globals,
			obj.func_name,
			obj.func_defaults,
			obj.func_closure,
			))
		self.write(pickle.REDUCE)
		self.memoize(obj)
	dispatch[types.FunctionType] = save_func

	def save_code(self, obj):
		assert type(obj) is types.CodeType
		self.save(marshal.loads)
		self.save((marshal.dumps(obj),))
		self.write(pickle.REDUCE)
		self.memoize(obj)
	dispatch[types.CodeType] = save_code

	def save_cell(self, obj):
		assert type(obj) is CellType
		self.save(makeCell)
		self.save((obj.cell_contents,))
		self.write(pickle.REDUCE)
		self.memoize(obj)
	dispatch[CellType] = save_cell

	# We also search for module dicts and reference them.
	def intellisave_dict(self, obj):
		if len(obj) <= 5: # fastpath
			self.save_dict(obj)
			return
		for modname, mod in sys.modules.iteritems():
			if not mod: continue
			moddict = mod.__dict__
			if obj is moddict:
				self.save(getModuleDict)
				self.save((modname,))
				self.write(pickle.REDUCE)
				self.memoize(obj)
				return
		self.save_dict(obj)
	dispatch[types.DictionaryType] = intellisave_dict

	# Some types in the types modules are not correctly referenced,
	# such as types.FunctionType. This is fixed here.
	def fixedsave_type(self, obj):
		try:
			self.save_global(obj)
			return
		except pickle.PicklingError:
			pass
		for modname in ["types"]:
			moddict = sys.modules[modname].__dict__
			for modobjname,modobj in moddict.iteritems():
				if modobj is obj:
					self.write(pickle.GLOBAL + modname + '\n' + modobjname + '\n')
					self.memoize(obj)
					return
		self.save_global(obj)
	dispatch[types.TypeType] = fixedsave_type

	# Wrap _batch_setitems (e.g. for dicts) so that our representations stays fixed
	# (the order of dict.keys() can be different at each run).
	orig_batch_setitems = pickle.Pickler._batch_setitems
	def _batch_setitems(self, items):
		items = sorted(items)
		self.orig_batch_setitems(iter(items))

	# Wrap save_reduce so that we can catch a few cases (e.g. set)
	# to fix up the representation so that it stays fixed (as for dicts).
	orig_save_reduce = pickle.Pickler.save_reduce
	def save_reduce(self, func, args, state=None, listitems=None, dictitems=None, obj=None):
		if func is set:
			assert len(args) == 1
			args = (sorted(args[0]),)
		self.orig_save_reduce(func=func, args=args, state=state, listitems=listitems, dictitems=dictitems, obj=obj)

	# avoid pickling instances of ourself. this mostly doesn't make sense and leads to trouble.
	# however, also doesn't break. it mostly makes sense to just ignore.
	def __getstate__(self): return None
	def __setstate__(self, state): pass
