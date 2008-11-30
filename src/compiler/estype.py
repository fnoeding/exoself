# 
# The BSD License
# 
# Copyright (c) 2008, Florian Noeding
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
# Neither the name of the of the author nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific
# prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#


from llvm.core import *



class ESType(object):
	''' represents types of data, not variables! '''

	def __init__(self, parents, payload):
		''' do not call directly! use construction methods '''
		assert(isinstance(parents, list))
		for x in parents:
			assert(isinstance(x, ESType))
		self.parents = parents
		self.payload = payload


	def derivePointer(self):
		return ESType([self], ('pointer', None))


	def dereference(self):
		assert(self.isPointer())

		return self.parents[0]


	def deriveConst(self):
		return ESType._simplify(ESType([self], ('const', None)))


	def deriveInvariant(self):
		# everything referenced by an invariant is also invariant
		return ESType._simplify(ESType([self], ('invariant', None)))


	def deriveTypedef(self, name):
		# break structural equivalence
		return ESType([self], ('typedef', name))


	@staticmethod
	def createStruct(name, parts, partNames):
		return ESType(parts, ('struct', name, partNames))


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
	def createNone():
		# move to estypesystem? but it should not be used as a normal type, only internally...
		return ESType([], ('elementary', 'none'))


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
			for i, p in enumerate(self.parents):
				# special case: self pointer --> opaque type
				if p._isSelfPointer():
					th = TypeHandle.new(Type.opaque())
					opaques.append(th)

					t = th.type
					while p.payload[0] == 'pointer':
						t = Type.pointer(t)

						assert(len(p.parents) == 1)
						p = p.parents[0]

					llvmTypes.append(t)
				else:
					llvmTypes.append(p.toLLVMType())

			s = Type.struct(llvmTypes)

			for th in opaques:
				th.type.refine(s)

			if not opaques:
				return s
			else:
				return th.type

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
			if t == u'int8' or t == u'uint8':
				return Type.int(8)
			elif t == u'int16' or t == u'uint16':
				return Type.int(16)
			elif t == u'int32' or t == u'uint32':
				return Type.int(32)
			elif t == u'int64' or t == u'uint64':
				return Type.int(64)
			elif t == u'bool':
				return Type.int(1)
			elif t == u'void':
				return Type.void()
			elif t == u'float32':
				return Type.float()
			elif t == u'float64':
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


	def isFunction(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		return p.payload[0] == 'function'


	def isPointer(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		if p.payload[0] == 'pointer':
			return True
		elif self.payload == ('elementary', 'none'):
			return True

		return False


	def isStruct(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		return p.payload[0] == 'struct'


	def _isSelfPointer(self):
		p = self
		while p.payload[0] == 'pointer':
			p = p.parents[0]

		return p.payload[0] == 'selfpointer'

	def isBoolean(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		if p.payload[0] != 'elementary':
			return False

		if p.payload[1] != 'bool':
			return False

		return True


	def isSignedInteger(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		if p.payload[0] != 'elementary':
			return False

		if p.payload[1] in ['int8', 'int16', 'int32', 'int64']:
			return True

		return False


	def isUnsignedInteger(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		if p.payload[0] != 'elementary':
			return False

		if p.payload[1] in ['uint8', 'uint16', 'uint32', 'uint64']:
			return True

		return False


	def isFloatingPoint(self):
		p = self
		while p.payload[0] == 'typedef':
			p = p.parents[0]

		if p.payload[0] != 'elementary':
			return False

		if p.payload[1] in ['float32', 'float64']:
			return True

		return False


	def getFunctionReturnTypes(self):
		assert(self.isFunction())

		n = self.payload[1]

		return self.parents[:n]


	def getFunctionParameterTypes(self):
		assert(self.isFunction())

		n = self.payload[1]

		return self.parents[n:]


	def getStructMembers(self):
		assert(self.isStruct())

		m = []
		for i in range(len(self.parents)):
			name = self.payload[2][i]
			type_ = self.parents[i]

			if type_._isSelfPointer():
				# replace selfpointer with real type
				type_ = self

				p = self.parents[i]
				while p.payload[0] == 'pointer':
					type_ = type_.derivePointer()

					assert(len(p.parents) == 1)
					p = p.parents[0]

			m.append((name, type_))

		return m


	def getStructMemberTypeByName(self, name):
		assert(self.isStruct())

		try:
			idx = self.getStructMemberIndexByName(name)
		except AssertionError:
			return None

		return self.getStructMembers()[idx][1]


	def getStructMemberIndexByName(self, name):
		assert(self.isStruct())

		for i in range(len(self.parents)):
			if name == self.payload[2][i]:
				return i

		raise AssertionError('getStructMemberIndexByName should always succeed as it is only called after type checking...')




	def mangleName(self, mode):
		if mode == 'default':
			return self._mangleNameDefault()
		elif mode == 'C':
			assert(0 and 'should not be called for C mangling')
		else:
			assert(0 and 'dead code path')


	def _mangleNameDefault(self):
		if self.payload[0] == 'elementary':
			return self.payload[1]
		elif self.payload[0] == 'function':
			nRets = self.payload[1]

			rets = [x._mangleNameDefault() for x in self.parents[:nRets]]
			params = [x._mangleNameDefault() for x in self.parents[nRets:]]

			s = []
			for x in rets:
				s.append('R%s' % x)

			for x in params:
				s.append('A%s' % x)

			return '_'.join(s)
		elif self.payload[0] == 'pointer':
			s = self.parents[0]._mangleNameDefault()

			return 'P' + s
		elif self.payload[0] == 'struct':
			return 'S%d%s' % (len(self.payload[1]), self.payload[1])
		elif self.payload[0] == 'typedef':
			return 'T%d%s' % (len(self.payload[1]), self.payload[1])
		else:
			raise NotImplementedError('TODO')



