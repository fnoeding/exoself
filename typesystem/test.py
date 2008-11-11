#!/usr/bin/python


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
		return ESType([self], ('const', None))


	def deriveInvariant(self):
		return ESType([self], ('invariant', None))


	def deriveTypedef(self, name):
		# break structural equivalence
		return ESType([self], ('typedef', name))

	@staticmethod
	def createStruct(name, parts):
		return ESType(parts, ('struct', name))

	
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


	def __eq__(self, other):
		if self.payload != other.payload:
			return False

		if len(self.parents) != len(other.parents):
			return False

		for i in range(len(self.parents)):
			if self.parents[i] != other.parents[i]:
				return False


		return True



	def __ne__(self, other):
		return not self.__eq__(other)



	def toLLVMType(self):
		if len(self.parents) > 1:
			assert(self.payload[0] == 'struct')
		if not self.parents:
			assert(self.payload[0] == 'elementary')

		if self.payload[0] == 'struct':
			raise NotImplementedError()
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
	assert(ts.find('int8') != ts.find('byte'))
	assert(ts.find('int32') == ts.find('int'))
	assert(ts.find('int64') == ts.find('long'))
	assert(ts.find('int64').derivePointer() == ts.find('int64ptr'))
	assert(ts.find('void').derivePointer() != ts.find('restrictedPointer'))



	# now create a structure
	i64i32 = ESType.createStruct('pkg_mod_i64i32', [ts.find('int64'), ts.find('int32')]) # struct {x as int64; y as int32}
	ts.addType(i64i32, 'i64i32')
	print ts.find('i64i32')

	p6432 = ESType.createStruct('pkg_mod_p6432', [ts.find('int64'), ts.find('int32')]) # struct {x as int64; y as int32}
	ts.addType(p6432, 'p6432')
	print ts.find('p6432')

	assert(ts.find('p6432') != ts.find('i64i32'))





if __name__ == '__main__':
	main()


