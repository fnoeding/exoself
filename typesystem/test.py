#!/usr/bin/python

# TODO discuss: invariant, const, final


import setuppaths

from llvm.core import *


class ESTypeError(Exception):
	pass



class ESType(object):
	def __init__(self, parents, payload):
		''' do not call directly! use construction methods '''
		assert(isinstance(parents, list))
		for x in parents:
			assert(isinstance(x, ESType))
		self.parents = parents
		self.payload = payload


	def derivePointer(self):
		return ESType([self], ('pointer', None))


	def deriveConst(self):
		return ESType._simplify(ESType([self], ('const', None)))


	def deriveInvariant(self):
		# everything referenced by an invariant is also invariant
		return ESType._simplify(ESType([self], ('invariant', None)))


	def deriveTypedef(self, name):
		# break structural equivalence
		return ESType([self], ('typedef', name))


	@staticmethod
	def createStruct(name, parts):
		return ESType(parts, ('struct', name))


	@staticmethod
	def createFunction(returnTypes, paramTypes):
		assert(len(returnTypes) >= 1)
		parts = []
		parts.extend(returnTypes)
		parts.extend(paramTypes)
		return ESType(parts, ('function', len(returnTypes)))

	@staticmethod
	def createSelfPointer():
		''' only valid inside structs! '''
		return ESType([], ('selfpointer', None))

	@staticmethod
	def _simplify(t):
		# removes unnecessary const / invariant nodes

		# const(const(X)) == const(X)
		# invariant(invariant(X)) == invariant(X)
		# const(invariant(X)) == invariant(X)
		# invariant(const(X)) == ??? --> assert(0)?
		if t.payload[0] == 'invariant':
			assert(len(t.parents) == 1)

			if t.parents[0].payload[0] == 'invariant':
				return t.parents[0]
			elif t.parents[0].payload[0] == 'const':
				# TODO
				pass
		elif t.payload[0] == 'const':
			assert(len(t.parents) == 1)

			if t.parents[0].payload[0] == 'const':
				return t.parents[0]
			elif t.parents[0].payload[0] == 'invariant':
				return t.parents[0]
				

		return t

	
	def __str__(self):
		if not self.parents:
			return str(self.payload)
		elif len(self.parents) == 1:
			return str(self.payload) + ' ' + str(self.parents[0])
		else:
			s = []
			for p in self.parents:
				s.append(str(p))

			return '%s { %s }' % (self.payload, ', '.join(s))


	def isEquivalentTo(self, other, structural):
		# structural equivalence: Skip any typedefs and ignore different struct names

		t1 = self
		t2 = other

		if structural:
			while t1.payload[0] == 'typedef':
				assert(len(t1.parents) == 1)
				t1 = t1.parents[0]

			while t2.payload[0] == 'typedef':
				assert(len(t2.parents) == 1)
				t2 = t2.parents[0]


		if structural and t1.payload[0] == 'struct' and t2.payload[0] == 'struct':
			pass
		elif t1.payload != t2.payload:
			return False

		if len(t1.parents) != len(t2.parents):
			return False

		for i in range(len(t1.parents)):
			if not t1.parents[i].isEquivalentTo(t2.parents[i], structural):
				return False


		return True



	def __eq__(self, other):
		raise NotImplementedError('use isEquivalentTo')



	def __ne__(self, other):
		raise NotImplementedError('use isEquivalentTo')



	def toLLVMType(self):
		if len(self.parents) > 1:
			assert(self.payload[0] in ['struct', 'function'])
		if not self.parents:
			assert(self.payload[0] == 'elementary')

		if self.payload[0] == 'struct':
			llvmTypes = []
			opaques = []
			for p in self.parents:
				# special case: self pointer --> opaque type
				if p.payload[0] == 'selfpointer':
					t = Type.opaque()
					opaques.append(t)
					llvmTypes.append(t)
				else:
					llvmTypes.append(p.toLLVMType())

			s = Type.struct(llvmTypes)

			# refine types
			for t in opaques:
				t.refine(Type.pointer(s))

			return s

		elif self.payload[0] == 'function':
			llvmTypes = []
			for p in self.parents:
				llvmTypes.append(p.toLLVMType())

			nRets = self.payload[1]
			rets = llvmTypes[:nRets]
			params = llvmTypes[nRets:]

			if nRets == 1:
				return Type.function(rets[0], params)
			else:
				# does not work in LLVM 2.3
				return Type.function(rets, params)
		elif self.payload[0] == 'elementary':
			t = self.payload[1]
			if t == 'int8':
				return Type.int(8)
			elif t == 'int16':
				return Type.int(16)
			elif t == 'int32':
				return Type.int(32)
			elif t == 'int64':
				return Type.int(64)
			elif t == 'bool':
				return Type.int(1)
			elif t == 'void':
				return Type.void()
			elif t == 'single':
				return Type.float()
			elif t == 'double':
				return Type.double()
			else:
				raise NotImplementedError('conversion to LLVM type is not supported for elementary type: %s' % t)
		elif self.payload[0] == 'pointer':
			# work around: in LLVM exists no 'void*', just use an byte sized pointer
			llvmT = self.parents[0].toLLVMType()
			if llvmT == Type.void():
				return Type.pointer(Type.int(8))
			else:
				return Type.pointer(llvmT)
		elif self.payload[0] in ['const', 'invariant', 'typedef']:
			return self.parents[0].toLLVMType()
		else:
			raise NotImplementedError('can not convert payload to LLVM type: %s' % self.payload)




class ESTypeSystem(object):
	def __init__(self):
		self.types = {}
		self.aliases = {}

		# add elementary types
		for i in [8, 16, 32, 64]:
			name = 'int%d' % i
			self.types[name] = ESType([], ('elementary', name))

		self.types['bool'] = ESType([], ('elementary', 'bool'))
		self.types['void'] = ESType([], ('elementary', 'void'))
		self.types['single'] = ESType([], ('elementary', 'single'))
		self.types['double'] = ESType([], ('elementary', 'double'))


	def find(self, name):
		return self.types[self.findBaseName(name)]


	def findBaseName(self, name):
		if name in self.types:
			return name

		while name in self.aliases:
			name = self.aliases[name]

		if name not in self.types:
			raise ESTypeError('type not found: %s' % name)

		return name


	def addAlias(self, oldName, newName):
		if newName in self.types or newName in self.aliases:
			raise ESTypeError('type name already used: %s' % newName)

		self.find(oldName)# make sure oldName really exists

		self.aliases[newName] = oldName


	def addType(self, type, name):
		assert(isinstance(type, ESType))

		if name in self.types or name in self.aliases:
			raise ESTypeError('type name already used: %s' % name)

		self.types[name] = type


	def areAliasing(self, n1, n2):
		t1 = self.findBaseName(n1)
		t2 = self.findBaseName(n2)

		return t1 == t2


	

		


def main():
	ts = ESTypeSystem()

	# create types for some scalar variables
	int32 = ts.find('int32') # x as int32
	print int32, '-->', int32.toLLVMType() # x as int32;
	int64 = ts.find('int64') # x as int64;
	print int64, '-->', int64.toLLVMType()
	int64ptr = ts.find('int64').derivePointer() # x as int64*;
	print int64ptr, '-->', int64ptr.toLLVMType()
	int64ptrptr = ts.find('int64').derivePointer().derivePointer() # x as int64**;
	print int64ptrptr, '-->', int64ptrptr.toLLVMType()


	# create some aliases for basic types
	ts.addAlias('int32', 'int') # alias int as int32
	int = ts.find('int')
	print int, '-->', int.toLLVMType()
	ts.addAlias('int64', 'long') # alias long as int64
	long = ts.find('long')
	print long, '-->', long.toLLVMType()


	# create some aliases for pointer types
	int64ptr = ts.find('int64').derivePointer()
	ts.addType(int64ptr, 'int64ptr')
	print int64ptr, '-->', int64ptr.derivePointer()


	# create some typedefs
	byte = ts.find('int8').deriveTypedef('pkg_mod_byte')
	ts.addType(byte, 'byte')
	print byte, '-->', byte.toLLVMType()
	assert(not ts.areAliasing('byte', 'int8'))
	restrictedPointer = ts.find('void').derivePointer().deriveTypedef('pkg_mod_restrictedPointer')
	ts.addType(restrictedPointer, 'restrictedPointer')
	print restrictedPointer, '-->', restrictedPointer.toLLVMType()
	print restrictedPointer.derivePointer(), '-->', restrictedPointer.derivePointer().toLLVMType()


	# do some tests
	assert(not ts.find('int8').isEquivalentTo(ts.find('byte'), False))
	assert(ts.find('int8').isEquivalentTo(ts.find('byte'), True))
	assert(ts.find('int32').isEquivalentTo(ts.find('int'), False))
	assert(ts.find('int32').isEquivalentTo(ts.find('int'), True))
	assert(ts.find('int64').isEquivalentTo(ts.find('long'), False))
	assert(ts.find('int64').isEquivalentTo(ts.find('long'), True))
	assert(ts.find('int64').derivePointer().isEquivalentTo(ts.find('int64ptr'), False))
	assert(not ts.find('void').derivePointer().isEquivalentTo(ts.find('restrictedPointer'), False))



	# now create a structure
	i64i32 = ESType.createStruct('pkg_mod_i64i32', [ts.find('int64'), ts.find('int32')]) # struct {x as int64; y as int32}
	ts.addType(i64i32, 'i64i32')
	print i64i32, '-->', i64i32.toLLVMType()

	p6432 = ESType.createStruct('pkg_mod_p6432', [ts.find('int64'), ts.find('int32')]) # struct {x as int64; y as int32}
	ts.addType(p6432, 'p6432')
	print p6432, '-->', p6432.toLLVMType()

	assert(not ts.find('p6432').isEquivalentTo(ts.find('i64i32'), False))
	assert(ts.find('p6432').isEquivalentTo(ts.find('i64i32'), True))


	# define a *recursive* structure
	linkedListContents = [ts.find('void').derivePointer(), ESType.createSelfPointer(), ESType.createSelfPointer()]
	linkedList = ESType.createStruct('pkg_mod_linkedList', linkedListContents)
	print linkedList, '-->', linkedList.toLLVMType()


	# create a function
	fi_bi = ESType.createFunction([ts.find('int')], [ts.find('byte'), ts.find('int')])
	ts.addType(fi_bi, 'fi_bi')
	print fi_bi, '-->', fi_bi.toLLVMType()

	fi_ci = ESType.createFunction([ts.find('int32')], [ts.find('int8'), ts.find('int32')])
	ts.addType(fi_ci, 'fi_ci')
	print fi_ci, '-->', fi_ci.toLLVMType()
	assert(not fi_ci.isEquivalentTo(fi_bi, False))
	assert(fi_ci.isEquivalentTo(fi_bi, True))


	# create an enum type
	# this is just a typedef
	enumX = ts.find('int32').deriveTypedef('pkg_mod_enumX') # enum(int32) enumX {a,b,c,d}
	print enumX, '-->', enumX.toLLVMType()
	assert(not enumX.isEquivalentTo(ts.find('int32'), False))
	assert(enumX.isEquivalentTo(ts.find('int32'), True))


	# const / invariant tests
	iint64ptr = ts.find('int64ptr').deriveInvariant()
	print iint64ptr, '-->', iint64ptr.toLLVMType()
	print 'invariant(invariant(int64*)):', iint64ptr.deriveInvariant()
	cint64ptr = ts.find('int64ptr').deriveConst()
	print cint64ptr, '-->', cint64ptr.toLLVMType()
	print 'const(const(int64*)):', cint64ptr.deriveConst()

	print 'FIXME? forbid this? invariant(const(int64*)):', ts.find('int64ptr').deriveConst().deriveInvariant()
	print 'const(invariant(int64*)):', ts.find('int64ptr').deriveInvariant().deriveConst()





if __name__ == '__main__':
	main()



