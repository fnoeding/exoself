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

import os
import estype
import estypesystem
from llvm.core import *

_dbgVersion = 6 << 16 # LLVMDebugVersion; FIXME use constant from LLVM bindings
_int1 = Type.int(1)
_int32 = Type.int(32)
_int64 = Type.int(64)
_pEmptyStruct = Type.pointer(Type.struct([]))
_pint8 = Type.pointer(Type.int(8))
_word = Type.int(64) # FIXME



class DebugInfoBuilder(object):
	class _State(object):
		pass


	def __init__(self):
		self._setupTypes()

		self._state = {} # modules --> state


	def _setupTypes(self):

		class Types(object):
			pass
		types = Types()
		self._types = types

		types.anchor = Type.struct([_int32, _int32])

		types.compileUnit = Type.struct([
			_int32,
			_pEmptyStruct,
			_int32,
			_pint8,
			_pint8,
			_pint8,
			])

		types.subprogram = Type.struct([
			_int32,
			_pEmptyStruct,
			_pEmptyStruct,
			_pint8,
			_pint8,
			_pint8,
			_pEmptyStruct,
			_int32,
			_pEmptyStruct,
			_int1,
			_int1,
			])

		types.basicType = Type.struct([
			_int32,
			_pEmptyStruct,
			_pint8,
			_pEmptyStruct,
			_int32,
			_int64,
			_int64,
			_int64,
			_int32,
			_int32,
			])

		types.derivedType = Type.struct([
			_int32,
			_pEmptyStruct,
			_pint8,
			_pEmptyStruct,
			_int32,
			_int64,
			_int64,
			_int64,
			_int32,
			_pEmptyStruct,
			])

		types.compositeType = Type.struct([
			_int32,
			_pEmptyStruct,
			_pint8,
			_pEmptyStruct,
			_int32,
			_int64,
			_int64,
			_int64,
			_int32,
			_pEmptyStruct,
			_pEmptyStruct,
			])

		types.globalVariable = Type.struct([
			_int32,
			_pEmptyStruct,
			_pEmptyStruct,
			_pint8,
			_pint8,
			_pint8,
			_pEmptyStruct,
			_int32,
			_pEmptyStruct,
			_int1,
			_int1,
			_pEmptyStruct,
			])

		types.variable = Type.struct([
			_int32,
			_pEmptyStruct,
			_pint8,
			_pEmptyStruct,
			_int32,
			_pEmptyStruct,
			])


	def setupModule(self, module, targetData):
		''' must be called once per module '''
		self._state[module] = DebugInfoBuilder._State()
		state = self._state[module]
		state.targetData = targetData
		state.typeDescriptors = {} # mangled type name -> LLVM global variable describing type

		# functions are accessed via module.get_function_named
		Function.intrinsic(module, INTR_DBG_STOPPOINT, [])
		Function.intrinsic(module, INTR_DBG_DECLARE, [])
		Function.intrinsic(module, INTR_DBG_FUNC_START, [])
		Function.intrinsic(module, INTR_DBG_REGION_START, [])
		Function.intrinsic(module, INTR_DBG_REGION_END, [])


		module.add_type_name('llvm.dbg.anchor.type', self._types.anchor)
		module.add_type_name('llvm.dbg.compile_unit.type', self._types.compileUnit)
		module.add_type_name('llvm.dbg.subprogram.type', self._types.subprogram)
		module.add_type_name('llvm.dbg.basictype.type', self._types.basicType)
		module.add_type_name('llvm.dbg.derivedtype.type', self._types.derivedType)
		module.add_type_name('llvm.dbg.compositetype.type', self._types.compositeType)
		module.add_type_name('llvm.dbg.variable.type', self._types.variable)
		module.add_type_name('llvm.dbg.global_variable.type', self._types.globalVariable)


	def _addGlobal(self, module, type, name, linkage, init):
		ref = module.add_global_variable(type, name)
		ref.linkage = linkage
		ref.global_constant = True
		ref.section = 'llvm.metadata'
		ref.initializer = init

		return ref


	def addGlobalInfo(self, module):
		''' should be called once per module (in principle only one module needs this, but inserting it in every module makes things easier) '''

		init = Constant.struct([
			Constant.int(_int32, 0 + _dbgVersion),
			Constant.int(_int32, 17),
			])
		compileUnits = self._addGlobal(module, self._types.anchor, 'llvm.dbg.compile_units', LINKAGE_LINKONCE, init)

		init = Constant.struct([
			Constant.int(_int32, 0 + _dbgVersion),
			Constant.int(_int32, 52),
			])
		globalVariables = self._addGlobal(module, self._types.anchor, 'llvm.dbg.global_variables', LINKAGE_LINKONCE, init)

		init = Constant.struct([
			Constant.int(_int32, 0 + _dbgVersion),
			Constant.int(_int32, 46),
			])
		subprograms = self._addGlobal(module, self._types.anchor, 'llvm.dbg.subprograms', LINKAGE_LINKONCE, init)


	def addCompileUnitInfo(self, module, absFilename):
		assert(os.path.isabs(absFilename))

		p, fn = os.path.split(absFilename)
		#p = p + '/' # trailing slash is important for pathData!

		srcData = Constant.stringz(fn)
		src = self._addGlobal(module, srcData.type, '__dbgstr', LINKAGE_INTERNAL, srcData)

		pathData = Constant.stringz(p) # trailing slash is important!
		path = self._addGlobal(module, pathData.type, '__dbgstr', LINKAGE_INTERNAL, pathData)

		producerData = Constant.stringz('Exoself Compiler by Florian Noeding <florian@noeding.com>')
		producer = self._addGlobal(module, producerData.type, '__dbgstr', LINKAGE_INTERNAL, producerData)

		gepIdx = [Constant.int(_word, 0), Constant.int(_word, 0)]
		init = Constant.struct([
			Constant.int(_int32, 17 + _dbgVersion),
			Constant.bitcast(module.get_global_variable_named('llvm.dbg.compile_units'), _pEmptyStruct),
			Constant.int(_int32, 4), # FIXME Dwarf language identifier (C89: 1, C: 2, C++: 4, userStart: 0x8000, userEnd: 0xffff)
			src.gep(gepIdx),
			path.gep(gepIdx),
			producer.gep(gepIdx),
			])
		compileUnit = self._addGlobal(module, self._types.compileUnit, 'llvm.dbg.compile_unit', LINKAGE_INTERNAL, init)



	def addFunctionInfoStart(self, module, builder, lineNumber, name, displayName):
		''' builder must be set to insert directly after the entry block '''

		nameData = Constant.stringz(name)
		name = self._addGlobal(module, nameData.type, '__dbgstr', LINKAGE_INTERNAL, nameData)

		displayNameData = Constant.stringz(displayName)
		displayName = self._addGlobal(module, displayNameData.type, '__dbgstr', LINKAGE_INTERNAL, displayNameData)


		gepIdx = [Constant.int(_word, 0), Constant.int(_word, 0)]
		init = Constant.struct([
			Constant.int(_int32, 46 + _dbgVersion),
			module.get_global_variable_named('llvm.dbg.subprograms').bitcast(_pEmptyStruct),
			module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct),
			name.gep(gepIdx),
			displayName.gep(gepIdx),
			Constant.null(_pint8), # MIPS linkage name TODO?
			module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct), # ref to compile unit, where this function is defined
			Constant.int(_int32, lineNumber),
			Constant.null(_pEmptyStruct), #basicType.bitcast(_pEmptyStruct), # FIXME add type information
			Constant.int(_int1, 0), # FIXME true iff the function is local to the compile unit (static)
			Constant.int(_int1, 1), # FIXME true iff the function is defined in the compile unit (not extern)
			])
		subprogram = self._addGlobal(module, self._types.subprogram, 'llvm.dbg.subprogram', LINKAGE_INTERNAL, init)

		builder.call(module.get_function_named('llvm.dbg.func.start'), [subprogram.bitcast(_pEmptyStruct)])

		return subprogram


	def addFunctionInfoEnd(self, module, builder, subprogram):
		# the call must be inserted before any terminator instructions!

		block = builder.block
		instrs = block.instructions
		if instrs:
			n = len(instrs) - 1
			while n >= 0 and instrs[n].is_terminator:
				n -= 1
			n += 1

			builder.position_before(instrs[n])



		builder.call(module.get_function_named('llvm.dbg.region.end'), [subprogram.bitcast(_pEmptyStruct)])
		builder.position_at_end(block)


	def addStopPoint(self, module, builder, lineNumber, columnNumber=0):
		stopPoint = module.get_function_named('llvm.dbg.stoppoint')
		compileUnit = module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct)

		builder.call(stopPoint, [Constant.int(_int32, lineNumber),
						Constant.int(_int32, columnNumber),
						compileUnit])


	def addLocalVariableInfo(self, module, builder, llvmRef, esType, subprogram, name, lineNumber, varType):
		varTypes = {}
		varTypes['auto'] = 256
		varTypes['arg'] = 257
		varTypes['ret'] = 258
		varType = varTypes[varType]

		nameData = Constant.stringz(name)
		name = self._addGlobal(module, nameData.type, '__dbgstr', LINKAGE_INTERNAL, nameData)

		compileUnit = module.get_global_variable_named('llvm.dbg.compile_unit')

		gepIdx = [Constant.int(_word, 0,), Constant.int(_word, 0)]
		init = Constant.struct([
			Constant.int(_int32, varType + _dbgVersion),
			subprogram.bitcast(_pEmptyStruct),
			name.gep(gepIdx),
			compileUnit.bitcast(_pEmptyStruct),
			Constant.int(_int32, lineNumber),
			#self._llvmRefToDebugTypeDesc(module, llvmRef)
			#Constant.null(_pEmptyStruct), # FIXME ref to type info
			self._esTypeToDebugTypeDesc(module, esType),
			])
		variable = self._addGlobal(module, self._types.variable, 'llvm.dbg.variable', LINKAGE_INTERNAL, init)


		declareVar = module.get_function_named('llvm.dbg.declare')
		builder.call(declareVar, [builder.bitcast(llvmRef, _pEmptyStruct), variable.bitcast(_pEmptyStruct)])


	def _esTypeToDebugTypeDesc(self, module, esType):
		state = self._state[module]
		typeDescs = state.typeDescriptors

		mangledName = esType.mangleName('default')

		try:
			return typeDescs[mangledName]
		except:
			pass

		if esType.isSignedInteger():
			size = esType.toLLVMType().width
			td = self._createIntType(module, 'int%d' % size, size, True)
		elif esType.isUnsignedInteger():
			size = esType.toLLVMType().width
			td = self._createIntType(module, 'int%d' % size, size, True)
		elif esType.isPointer():
			td = self._createPointerType(module, 'ptrXXX', esType)
		elif esType.isStruct():
			td = self._createStructType(module, 'structXXX', esType)
		#elif esType.isFunction():
		elif esType.isBoolean():
			td = self._createBooleanType(module, 'bool')
		elif esType.isFloatingPoint():
			llvmT = esType.toLLVMType()
			if llvmT.kind == TYPE_FLOAT:
				size = 32
			elif llvmT.kind == TYPE_DOUBLE:
				size = 64
			else:
				raise NotImplementedError()
			td = self._createFloatType(module, 'float%d' % size, 'float%d' % size)
		else:
			return Constant.null(_pEmptyStruct)

		typeDescs[mangledName] = td.bitcast(_pEmptyStruct)
		return td.bitcast(_pEmptyStruct)


	def _createBasicType(self, module, typeName, typeSize, typeAlignment, typeOffset, typeEncoding):
		''' encoding is one of 'address', 'boolean', 'float', 'signed', 'signed_char', 'unsigned', 'unsigned_char' '''

		typeEncodings = {}
		typeEncodings['address'] = 1
		typeEncodings['boolean'] = 2
		typeEncodings['float'] = 4
		typeEncodings['signed'] = 5
		typeEncodings['signed_char'] = 6
		typeEncodings['unsigned'] = 7
		typeEncodings['unsigned_char'] = 8
		typeEncoding = typeEncodings[typeEncoding]

		# do not create duplicate types in this module!

		typeNameData = Constant.stringz(typeName)
		typeName = self._addGlobal(module, typeNameData.type, '__dbgstr', LINKAGE_INTERNAL, typeNameData)

		gepIdx = [Constant.int(_word, 0), Constant.int(_word, 0)]

		init = Constant.struct([
			Constant.int(_int32, 36 + _dbgVersion),
			module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct),
			typeName.gep(gepIdx),
			Constant.null(_pEmptyStruct), # FIXME ref to compile unit of type def
			Constant.int(_int32, 0), # FIXME line number of type definition
			Constant.int(_int64, typeSize),
			Constant.int(_int64, typeAlignment),
			Constant.int(_int64, typeOffset),
			Constant.int(_int32, 0), # FIXME this field is used by llvm-gcc... any idea what to insert here?
			Constant.int(_int32, typeEncoding),
			])

		basicType = self._addGlobal(module, self._types.basicType, 'llvm.dbg.basictype', LINKAGE_INTERNAL, init)

		return basicType

	def _createDerivedType(self, module, typeName, tag, typeSize, typeAlignment, typeOffset, baseType):
		tags = {}
		tags['formalParameter'] = 5
		tags['member'] = 13
		tags['pointerType'] = 15
		tags['referenceType'] = 16
		tags['typedef'] = 22
		tags['constType'] = 38
		tags['volatileType'] = 53
		tags['restrictType'] = 55
		tag = tags[tag]

		typeNameData = Constant.stringz(typeName)
		typeName = self._addGlobal(module, typeNameData.type, '__dbgstr', LINKAGE_INTERNAL, typeNameData)

		gepIdx = [Constant.int(_word, 0), Constant.int(_word, 0)]

		init = Constant.struct([
			Constant.int(_int32, tag + _dbgVersion),
			module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct),
			typeName.gep(gepIdx),
			Constant.null(_pEmptyStruct), # FIXME ref to compile unit of type def
			Constant.int(_int32, 0), # FIXME line number of def
			Constant.int(_int64, typeSize),
			Constant.int(_int64, typeAlignment),
			Constant.int(_int64, typeOffset),
			Constant.int(_int32, 0), # FIXME this field is used by llvm-gcc... any idea what to insert here?
			baseType.bitcast(_pEmptyStruct),
			])

		derivedType = self._addGlobal(module, self._types.derivedType, 'llvm.dbg.derivedtype', LINKAGE_INTERNAL, init)

		return derivedType


	def _createCompositeType(self, module, typeName, tag, typeSize, typeAlignment, typeOffset, derivedFrom, elements, existingGlobal=None):
		tags = {}
		tags['arrayType'] = 1
		tags['enumerationType'] = 4
		tags['structureType'] = 19
		tags['unionType'] = 23
		tags['vectorType'] = 259
		tags['subroutineType'] = 46
		tags['inheritance'] = 26
		tag = tags[tag]


		typeNameData = Constant.stringz(typeName)
		typeName = self._addGlobal(module, typeNameData.type, '__dbgstr', LINKAGE_INTERNAL, typeNameData)

		gepIdx = [Constant.int(_word, 0), Constant.int(_word, 0)]

		init = Constant.struct([
			Constant.int(_int32, tag + _dbgVersion),
			module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct),
			typeName.gep(gepIdx),
			Constant.null(_pEmptyStruct), # FIXME ref to compile unit of type def
			Constant.int(_int32, 0), # FIXME line number of def
			Constant.int(_int64, typeSize),
			Constant.int(_int64, typeAlignment),
			Constant.int(_int64, typeOffset),
			Constant.int(_int32, 0), # flags???
			derivedFrom.bitcast(_pEmptyStruct),
			elements.bitcast(_pEmptyStruct),
			])

		if not existingGlobal:
			derivedType = self._addGlobal(module, self._types.compositeType, 'llvm.dbg.compositetype', LINKAGE_INTERNAL, init)
		else:
			derivedType = existingGlobal
			derivedType.initializer = init

		return derivedType



	def _createBooleanType(self, module, name):
		state = self._state[module]

		alignment = 8 * state.targetData.abi_alignmentof_type(_int1)
		offset = 0
		size = 8 * state.targetData.abi_sizeof_type(_int1)
		return self._createBasicType(module, name, size, alignment, offset, 'boolean')


	def _createIntType(self, module, name, size, signed):
		state = self._state[module]

		llvmType = Type.int(size)
		alignment = 8 * state.targetData.abi_alignmentof_type(llvmType)
		offset = 0
		if signed:
			encoding = 'signed'
		else:
			encoding = 'unsigned'
		return self._createBasicType(module, name, size, alignment, offset, encoding)


	def _createFloatType(self, module, name, which):
		state = self._state[module]

		if which == 'float32':
			size = 32
			offset = 0
			alignment = 8 * state.targetData.abi_alignmentof_type(Type.float())
		elif which == 'float64':
			size = 64
			offset = 0
			alignment = 8 * state.targetData.abi_alignmentof_type(Type.double())
		else:
			assert(0 and 'dead code path')

		return self._createBasicType(module, name, size, alignment, offset, 'float')


	def _createPointerType(self, module, name, esType):
		state = self._state[module]

		llvmType = esType.toLLVMType()

		alignment = 8 * state.targetData.abi_alignmentof_type(llvmType)
		offset = 0
		size = _word.width

		esTypeDeref = esType.dereference()
		if esTypeDeref.isVoid():
			baseType = Constant.null(_pEmptyStruct)
		else:
			baseType = self._esTypeToDebugTypeDesc(module, esTypeDeref)

		return self._createDerivedType(module, name, 'pointerType', size, alignment, offset, baseType)


	def _createStructType(self, module, name, esType):
		state = self._state[module]

		# needs special care due to recursive structs like linked lists
		# so first create a place holder entry in the type descriptor table before doing any real work
		typeDescs = state.typeDescriptors
		compositeType = self._addGlobal(module, self._types.compositeType, 'llvm.dbg.compositetype', LINKAGE_INTERNAL, Constant.null(self._types.compositeType)) # the real init will be applied later
		mangledName = esType.mangleName('default')
		assert(mangledName not in typeDescs)
		typeDescs[mangledName] = compositeType




		llvmType = esType.toLLVMType()

		alignment = 8 * state.targetData.abi_alignmentof_type(llvmType)
		offset = 0
		size = 8 * state.targetData.abi_sizeof_type(llvmType)

		derivedFrom = Constant.null(_pEmptyStruct)
		members = esType.getStructMembers() # name -> esType
		elementsData = []
		for i, m in enumerate(members):
			tLLVM = m[1].toLLVMType()

			tSize = 8 * state.targetData.abi_sizeof_type(tLLVM)
			tAlignment = 8 * state.targetData.abi_alignmentof_type(tLLVM)
			tOffset = 8 * state.targetData.offsetof_element_in_struct(llvmType, i)
			t = self._esTypeToDebugTypeDesc(module, m[1])
			dt = self._createDerivedType(module, m[0], 'member', tSize, tAlignment, tOffset, t)

			elementsData.append(dt.bitcast(_pEmptyStruct))
		elementsData = Constant.array(_pEmptyStruct, elementsData)
		elements = self._addGlobal(module, elementsData.type, 'llvm.dbg.array', LINKAGE_INTERNAL, elementsData)


		return self._createCompositeType(module, name, 'structureType', size, alignment, offset, derivedFrom, elements, existingGlobal=compositeType)



