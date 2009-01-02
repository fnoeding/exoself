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
from llvm.core import *

_dbgVersion = 6 << 16 # LLVMDebugVersion; FIXME use constant from LLVM bindings
_int1 = Type.int(1)
_int32 = Type.int(32)
_int64 = Type.int(64)
_pEmptyStruct = Type.pointer(Type.struct([]))
_pint8 = Type.pointer(Type.int(8))

class Types(object):
	pass


def _setupTypes():
	Types.anchor = Type.struct([_int32, _int32])

	Types.compileUnit = Type.struct([
		_int32,
		_pEmptyStruct,
		_int32,
		_pint8,
		_pint8,
		_pint8,
		])

	Types.subprogram = Type.struct([
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

	Types.basicType = Type.struct([
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

	Types.globalVariable = Type.struct([
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

	Types.variable = Type.struct([
		_int32,
		_pEmptyStruct,
		_pint8,
		_pEmptyStruct,
		_int32,
		_pEmptyStruct,
		])


_setupTypes()




def addIntrinsics(module):
	''' returns dict with mapping from 'stopPoint', 'declare', 'funcStart', 'regionStart', 'regionEnd' to intrinsics in given module
	must be called once per module
	'''
	d = {}
	d['stopPoint'] = Function.intrinsic(module, INTR_DBG_STOPPOINT, [])
	d['declare'] = Function.intrinsic(module, INTR_DBG_DECLARE, [])
	d['funcStart'] = Function.intrinsic(module, INTR_DBG_FUNC_START, [])
	d['regionStart'] = Function.intrinsic(module, INTR_DBG_REGION_START, [])
	d['regionEnd'] = Function.intrinsic(module, INTR_DBG_REGION_END, [])


	return d


def addTypes(module):
	''' should be called once per module (but is optional, makes .ll more readable) '''
	module.add_type_name('llvm.dbg.anchor.type', Types.anchor)
	module.add_type_name('llvm.dbg.compile_unit.type', Types.compileUnit)
	module.add_type_name('llvm.dbg.subprogram.type', Types.subprogram)
	module.add_type_name('llvm.dbg.basictype.type', Types.basicType)


def _addGlobal(module, type, name, linkage, init):
	ref = module.add_global_variable(type, name)
	ref.linkage = linkage
	ref.global_constant = True
	ref.section = 'llvm.metadata'
	ref.initializer = init

	return ref


def addGlobalInfo(module):
	''' should be called once per module (in principle only one module needs this, but inserting it in every module makes things easier) '''

	init = Constant.struct([
		Constant.int(_int32, 0 + _dbgVersion),
		Constant.int(_int32, 17),
		])
	compileUnits = _addGlobal(module, Types.anchor, 'llvm.dbg.compile_units', LINKAGE_LINKONCE, init)

	init = Constant.struct([
		Constant.int(_int32, 0 + _dbgVersion),
		Constant.int(_int32, 52),
		])
	globalVariables = _addGlobal(module, Types.anchor, 'llvm.dbg.global_variables', LINKAGE_LINKONCE, init)

	init = Constant.struct([
		Constant.int(_int32, 0 + _dbgVersion),
		Constant.int(_int32, 46),
		])
	subprograms = _addGlobal(module, Types.anchor, 'llvm.dbg.subprograms', LINKAGE_LINKONCE, init)


def addCompileUnitInfo(module, absFilename):
	assert(os.path.isabs(absFilename))

	p, fn = os.path.split(absFilename)
	#p = p + '/' # trailing slash is important for pathData!

	srcData = Constant.stringz(fn)
	src = _addGlobal(module, srcData.type, '__dbgstr', LINKAGE_INTERNAL, srcData)

	pathData = Constant.stringz(p) # trailing slash is important!
	path = _addGlobal(module, pathData.type, '__dbgstr', LINKAGE_INTERNAL, pathData)

	producerData = Constant.stringz('Exoself Compiler by Florian Noeding <florian@noeding.com>')
	producer = _addGlobal(module, producerData.type, '__dbgstr', LINKAGE_INTERNAL, producerData)

	gepIdx = [Constant.int(_int32, 0), Constant.int(_int32, 0)]
	init = Constant.struct([
		Constant.int(_int32, 17 + _dbgVersion),
		Constant.bitcast(module.get_global_variable_named('llvm.dbg.compile_units'), _pEmptyStruct),
		Constant.int(_int32, 1), # Dwarf language identifier
		src.gep(gepIdx),
		path.gep(gepIdx),
		producer.gep(gepIdx),
		])
	compileUnit = _addGlobal(module, Types.compileUnit, 'llvm.dbg.compile_unit', LINKAGE_INTERNAL, init)



def addFunctionInfoStart(module, builder, lineNumber, name, displayName):
	''' builder must be set to insert directly after the entry block '''

	'''
	typeNameData = Constant.stringz('void') # FIXME
	typeName = _addGlobal(module, typeNameData.type, '__dbgstr', LINKAGE_INTERNAL, typeNameData)

	gepIdx = [Constant.int(_int32, 0), Constant.int(_int32, 0)]

	init = Constant.struct([
		Constant.int(_int32, 36 + _dbgVersion),
		module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct),
		typeName.gep(gepIdx),
		Constant.null(_pEmptyStruct), # FIXME ref to compile unit of type def
		Constant.int(_int32, 0), # FIXME line number of type definition
		Constant.int(_int64, 32), # FIXME type size in bits
		Constant.int(_int64, 32), # FIXME alignment in bits
		Constant.int(_int64, 0), # FIXME offset in bits
		Constant.int(_int32, 0), # ???
		Constant.int(_int32, 5), # ???
		])
	basicType = _addGlobal(module, Types.basicType, 'llvm.dbg.basictype', LINKAGE_INTERNAL, init)
	'''


	nameData = Constant.stringz(name)
	name = _addGlobal(module, nameData.type, '__dbgstr', LINKAGE_INTERNAL, nameData)

	displayNameData = Constant.stringz(displayName)
	displayName = _addGlobal(module, displayNameData.type, '__dbgstr', LINKAGE_INTERNAL, displayNameData)


	gepIdx = [Constant.int(_int32, 0), Constant.int(_int32, 0)]
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
	subprogram = _addGlobal(module, Types.subprogram, 'llvm.dbg.subprogram', LINKAGE_INTERNAL, init)

	builder.call(module.get_function_named('llvm.dbg.func.start'), [subprogram.bitcast(_pEmptyStruct)])

	return subprogram


def addFunctionInfoEnd(module, builder, subprogram):
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


def addStopPoint(module, builder, lineNumber, columnNumber=0):
	stopPoint = module.get_function_named('llvm.dbg.stoppoint')
	compileUnit = module.get_global_variable_named('llvm.dbg.compile_unit').bitcast(_pEmptyStruct)

	builder.call(stopPoint, [Constant.int(_int32, lineNumber),
					Constant.int(_int32, columnNumber),
					compileUnit])


def addLocalVariableInfo(module, builder, llvmRef, subprogram, name, lineNumber, varType):
	varTypes = {}
	varTypes['auto'] = 256
	varTypes['arg'] = 257
	varTypes['ret'] = 258
	varType = varTypes[varType]

	nameData = Constant.stringz(name)
	name = _addGlobal(module, nameData.type, '__dbgstr', LINKAGE_INTERNAL, nameData)

	compileUnit = module.get_global_variable_named('llvm.dbg.compile_unit')

	gepIdx = [Constant.int(_int32, 0,), Constant.int(_int32, 0)]
	init = Constant.struct([
		Constant.int(_int32, varType + _dbgVersion),
		subprogram.bitcast(_pEmptyStruct),
		name.gep(gepIdx),
		compileUnit.bitcast(_pEmptyStruct),
		Constant.int(_int32, lineNumber),
		Constant.null(_pEmptyStruct), # FIXME ref to type info
		])
	variable = _addGlobal(module, Types.variable, 'llvm.dbg.variable', LINKAGE_INTERNAL, init)


	declareVar = module.get_function_named('llvm.dbg.declare')
	builder.call(declareVar, [builder.bitcast(llvmRef, _pEmptyStruct), variable.bitcast(_pEmptyStruct)])





