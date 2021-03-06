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
from __future__ import with_statement

import setuppaths

from llvm import *
from llvm.core import *
from llvm.ee import *

import os.path
import re

from esfunction import ESFunction
from esvalue import ESValue
from esvariable import ESVariable
from estype import ESType
from errors import *
import astwalker
from tree import Tree, TreeType
import typeannotator
import llvmdebug






class ModuleTranslator(astwalker.ASTWalker):
	def _addHelperFunctionsPreTranslation(self):
		# int puts(char *);
		returnTypes = [self._findSymbol(name=u'int32', type_=ESType)]
		paramTypes = [self._findSymbol(name=u'int8', type_=ESType).derivePointer()]
		esType = ESType.createFunction(returnTypes, paramTypes)
		esFunc = ESFunction(u'puts', '', '', esType, [u's'], mangling='C', linkage='extern')
		self._addSymbol(name=u'puts', symbol=esFunc)
		type = esType.toLLVMType()
		func = self._module.add_function(type, 'puts')


		# void abort();
		returnTypes = [self._findSymbol(name=u'void', type_=ESType)]
		paramTypes = []
		esType = ESType.createFunction(returnTypes, paramTypes)
		esFunc = ESFunction(u'abort', '', '', esType, [], mangling='C', linkage='extern')
		type = esType.toLLVMType()
		func = self._module.add_function(type, 'abort')



	def _addHelperFunctionsPostTranslation(self):
		# if this module contains a main function emit code which will call it

		flist = self._findSymbol(name=u'main', type_=ESFunction, mayFail=True)

		if flist:
			assert(len(flist) == 1)
			esMain = flist[0]

			s = []
			s.append('The main function defined in this module has an unsupported signature.')
			s.append('supported signatures:')
			s.append('\tdef main() as int32')
			s.append('\tdef main() as void')

			int32 = self._findSymbol(name=u'int32', type_=ESType)
			void = self._findSymbol(name=u'void', type_=ESType)
			validA = ESType.createFunction([int32], [])
			validB = ESType.createFunction([void], [])

			ok = False
			for x in [validA, validB]:
				if x.isEquivalentTo(esMain.esType, False):
					ok = True

			if not ok:
				self._raiseException(RecoverableCompileError, postText=s)


			# has arguments?
			if len(esMain.esType.getFunctionParameterTypes()) == 0:
				functionType= Type.function(Type.int(32), [])
				function = self._module.add_function(functionType, 'main')

				entryBB = function.append_basic_block('entry')
				BB = function.append_basic_block('bb')

				b = Builder.new(entryBB)
				if self._debugMode:
					dbgSubProg = self._debugInfoBuilder.addFunctionInfoStart(module=self._module, builder=b, lineNumber=0, name='main', displayName='main')
				b.branch(BB)


				b = Builder.new(BB)
				r = b.call(esMain.llvmRef, [])

				retTypes = esMain.esType.getFunctionReturnTypes()
				assert(len(retTypes) == 1)

				if retTypes[0].toLLVMType() != Type.void():
					b.ret(r)
				else:
					b.ret(Constant.int(Type.int(32), 0))

				if self._debugMode:
					self._debugInfoBuilder.addFunctionInfoEnd(module=self._module, builder=b, subprogram=dbgSubProg)
			else:
				# TODO implement version with parameters
				self._raiseException(RecoverableCompileError, postText=s)


	def _addModuleXTors(self):
		# create *appending* global_ctors and global_dtors variables
		ft = Type.pointer(Type.function(Type.void(), []))
		st = Type.struct([Type.int(32), ft])

		def addXTors(xtors, what):
			assert what in ['ctors', 'dtors']

			if not xtors:
				return

			t = Type.array(st, len(xtors))
			gvar = self._module.add_global_variable(t, 'llvm.global_%s' % what)
			gvar.linkage = LINKAGE_APPENDING

			elems = []
			for x in xtors:
				prio = Constant.int(Type.int(32), 65535)
				func = x.llvmRef
				elems.append(Constant.struct([prio, func]))

			init = Constant.array(st, elems)
			gvar.initializer = init

		addXTors(self._moduleCTors, 'ctors')
		addXTors(self._moduleDTors, 'dtors')


	def _setupDebugInformation(self):
		if not self._debugMode:
			return

		self._debugInfoBuilder = llvmdebug.DebugInfoBuilder()
		self._debugInfoBuilder.setupModule(self._module, self._targetData)
		self._debugInfoBuilder.addGlobalInfo(self._module)
		self._debugInfoBuilder.addCompileUnitInfo(self._module, self._filename)


	def _findCurrentFunction(self):
		for x in reversed(self._nodes):
			if x.type == TreeType.DEFFUNC:
				return x.esFunction

		assert(0 and 'no function found - type checker should have prevented this!')


	def _onModuleStart(self, ast, packageName, moduleName, statements):
		self._errors = 0
		self._warnings = 0

		self._module = Module.new(ast.moduleName)
		self._moduleNode = ast

		self._moduleCTors = ast.moduleCTors
		self._moduleDTors = ast.moduleDTors

		# setup target and data layout
		self._targetData = TargetData.new('e-p:64:64:64-i1:8:8-i8:8:8-i16:16:16-i32:32:32-i64:64:64-f32:32:32-f64:64:64-v64:64:64-v128:128:128-a0:0:64-s0:64:64-f80:128:128')# FIXME; this is just the llvm-gcc default for x86_64-unknown-linux-gnu

		self._module.data_layout = str(self._targetData) # FIXME
		self._module.target = 'x86_64-unknown-linux-gnu' # FIXME

		# setup debug Info
		self._setupDebugInformation()

		# add some helper functions / prototypes / ... to the module
		self._addHelperFunctionsPreTranslation()

		# first add global variables
		for x in statements:
			if x.type == TreeType.DEFGLOBAL:
				self._dispatch(x)

		# imported global variables don't have llvmRef entries: add them
		for k, v in ast.symbolTable.getAllSymbols().iteritems():
			if not isinstance(v, ESVariable):
				continue

			if getattr(v, 'llvmRef', None):
				continue

			# can't reuse _onDefGlobal at the moment, since we need to declare an "extern" global variable

			llvmType = v.toLLVMType()
			mangledName = v.mangleName()
			v.llvmRef = self._module.add_global_variable(llvmType, mangledName)

			# use default linkage: external



		# translate
		for x in statements:
			# skip globals, as they were already handled above
			if x.type == TreeType.DEFGLOBAL:
				continue

			try:
				self._dispatch(x)
			except RecoverableCompileError, e:
				print e.message.rstrip()
				self._errors += 1
			except CompileError, e:
				print e.message.rstrip()
				self._errors += 1
				break

		if self._errors:
			raise CompileError('errors occured during compilation: aborting')

		# set module ctors, dtors
		self._addModuleXTors()

		# finally add some more helper functions / prototypes / ... to the module
		self._addHelperFunctionsPostTranslation()



	def _onImportAll(self, ast, moduleName):
		pass



	def _onDefFunction(self, ast, modifierKeys, modifierValues, name, returnTypeName, parameterNames, parameterTypeNames, block):
		esFunction = ast.esFunction
		esType = esFunction.esType

		try:
			# make really sure there is no function with this name
			llvmRef =  self._module.get_function_named(esFunction.mangledName)
		except LLVMException:
			llvmRef = None

		if llvmRef:
			if not llvmRef.is_declaration:
				s1 = 'mangled name already in use: %s' % esFunction.mangledName
				s2 ='This can be caused by defining a function with the same signature multiple times. If that\'s not the case please submit a bugreport with a testcase.'
				self._raiseException(CompileError, tree=ast.getChild(1), inlineText=s1, postText=s2)
		else:
			llvmRef = self._module.add_function(esType.toLLVMType(), esFunction.mangledName)
		esFunction.llvmRef = llvmRef # provide access through symbol table
		ast.llvmRef = llvmRef # provide direct access through ast node

		# set parameter names
		for i,x in enumerate(parameterNames):
			llvmRef.args[i].name = x.text


		if not block:
			return


		entryBB = llvmRef.append_basic_block('entry')
		bEntry = Builder.new(entryBB)
		if self._debugMode:
			dbgSubProg = self._debugInfoBuilder.addFunctionInfoStart(module=self._module, builder=bEntry, lineNumber=ast.line, name=esFunction.name, displayName=esFunction.name)
			ast.dbgSubProg = dbgSubProg


		# add variables
		for i,x in enumerate(parameterNames):
			var = self._findSymbol(name=x.text, type_=ESVariable)
			var.llvmRef = self._createAllocaForVar(x.text, var.toLLVMType(), llvmRef.args[i])

			if self._debugMode:
				self._debugInfoBuilder.addLocalVariableInfo(module=self._module, builder=bEntry, llvmRef=var.llvmRef, esType=var.esType, subprogram=dbgSubProg, name=x.text, lineNumber=x.line, varType='arg')

		# branch from entry to real code block and dispatch function body
		bb = llvmRef.append_basic_block('bb')
		self._currentBuilder = Builder.new(bb)
		bEntry.branch(bb)
		self._dispatch(block)

		returnTypes = esFunction.esType.getFunctionReturnTypes()
		bb = self._currentBuilder.block
		if not (bb.instructions and bb.instructions[-1].is_terminator):
			if len(returnTypes) == 1 and returnTypes[0].toLLVMType() == Type.void():
				self._currentBuilder.ret_void()
			else:
				s = self._generateContext(preText='warning:', postText='control flow possibly reaches end of non-void function. Inserting trap instruction...', lineBase1=block.line, numAfter=3)
				trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
				self._currentBuilder.call(trapFunc, [])
				self._currentBuilder.ret(Constant.int(Type.int(32), -1)) # and return, otherwise func.verify will fail

		if self._debugMode:
			self._debugInfoBuilder.addFunctionInfoEnd(module=self._module, builder=self._currentBuilder, subprogram=dbgSubProg)

		llvmRef.verify()



	def _onBlock(self, ast, blockContent):
		for x in blockContent:
			if self._debugMode:
				self._debugInfoBuilder.addStopPoint(self._module, self._currentBuilder, x.line, x.charPos)
			self._dispatch(x)



	def _onReturn(self, ast, expressions):
		esFunction = None
		for n in reversed(self._nodes):
			if n.type == TreeType.DEFFUNC:
				esFunction = n.esFunction
				break
		assert(esFunction)

		returnTypes = esFunction.esType.getFunctionReturnTypes()
		assert(len(returnTypes) == 1)
		if returnTypes[0].toLLVMType() == Type.void():
			assert(not expressions)
			self._currentBuilder.ret_void()
		else:
			self._dispatch(expressions[0])
			llvmValue = expressions[0].llvmValue
			self._currentBuilder.ret(llvmValue)


	def _onAssert(self, ast, expression):
		self._dispatch(expression)

		# TODO add a compiler switch to disable asserts, so they become noop's
		# TODO add a compiler switch to disable inclusion of context data


		# if value is statically available bail out now / warn
		# this does not work... investigate later
		#if value == Constant.int(Type.int(1), 0):
		#	print 'assert is always False in %s:%d' % ('???', ast.line())


		# find current function
		llvmFunc = self._findCurrentFunction().llvmRef

		# now implement an if

		thenBB = llvmFunc.append_basic_block('assert_true') # trap path
		elseBB = llvmFunc.append_basic_block('assert_false')

		cond = self._currentBuilder.not_(expression.llvmValue)
		self._currentBuilder.cbranch(cond, thenBB, elseBB)


		thenBuilder = Builder.new(thenBB)

		# build error string
		if ast.line:
			errorStringConst = 'assert failed! file %s line %d:\n' % (self._filename, ast.line)

			start = max(ast.line - 1 - 5, 0)
			stop = min(ast.line - 1 + 1, len(self._sourcecodeLines))
			for i in range(start, stop):
				errorStringConst += '% 5d: %s' % (i + 1, self._sourcecodeLines[i])
				if i != stop - 1:
					errorStringConst += '\n'
			errorStringConst += ' # <----- failed\n'
		else:
			errorStringConst = '(unknown) assert failed!'
		errorStringConst = Constant.stringz(errorStringConst);
		errorString = self._module.add_global_variable(errorStringConst.type, 'assertErrorString')
		errorString.initializer = errorStringConst
		errorString.global_constant = True

		word = self._findSymbol(name=u'word', type_=ESType).toLLVMType()
		idx = [Constant.int(word, 0), Constant.int(word, 0)]
		errorStringGEP = errorString.gep(idx)
		puts = self._module.get_function_named('puts')
		thenBuilder.call(puts, [errorStringGEP])

		# emit abort
		abortFunc = self._module.get_function_named('abort')
		thenBuilder.call(abortFunc, [])
		thenBuilder.branch(elseBB) # we'll never get here - but create proper structure of IR

		self._currentBuilder = Builder.new(elseBB)


	def _onIf(self, ast, expressions, blocks, elseBlock):
		llvmFunc = self._findCurrentFunction().llvmRef



		mergeBB = llvmFunc.append_basic_block('if_merge')
		for i in range(len(expressions)):
			thenBB = llvmFunc.append_basic_block('if_then')
			elseBB = llvmFunc.append_basic_block('if_else')

			self._dispatch(expressions[i])
			self._currentBuilder.cbranch(expressions[i].llvmValue, thenBB, elseBB)

			# generate code for then branch
			self._currentBuilder = Builder.new(thenBB)
			self._dispatch(blocks[i])

			# branch to mergeBB, but only if there was no terminator instruction
			currentBB = self._currentBuilder.block
			if not (currentBB.instructions and currentBB.instructions[-1].is_terminator):
				self._currentBuilder.branch(mergeBB)

			# continue with next else if / else
			self._currentBuilder = Builder.new(elseBB)
		if elseBlock:
			self._dispatch(elseBlock)

		# close last elseBB
		currentBB = self._currentBuilder.block
		if not (currentBB.instructions and currentBB.instructions[-1].is_terminator):
			self._currentBuilder.branch(mergeBB)

		# continue in mergeBB
		self._currentBuilder = Builder.new(mergeBB)


	def _onFor(self, ast, variableName, rangeStart, rangeStop, rangeStep, block):


		if rangeStart:
			self._dispatch(rangeStart)
			start = rangeStart.llvmValue
		else:
			start = Constant.int(Type.int(32), 0) # FIXME allow other types
		self._dispatch(rangeStop)
		stop = rangeStop.llvmValue
		if rangeStep:
			self._dispatch(rangeStep)
			step = rangeStep.llvmValue
		else:
			step = Constant.int(Type.int(32), 1) # FIXME allow other types

		inductVar = self._findSymbol(fromTree=variableName, type_=ESVariable)
		if not hasattr(inductVar, 'llvmRef'):
			inductVar.llvmRef = self._createAllocaForVar(variableName.text, inductVar.esType.toLLVMType())

		# setup loop by initializing induction variable
		self._currentBuilder.store(start, inductVar.llvmRef)

		# create blocks
		llvmFunc = self._findCurrentFunction().llvmRef
		headBB = llvmFunc.append_basic_block('head') # decide between Up and Down
		headDownBB = llvmFunc.append_basic_block('headDown')
		headUpBB = llvmFunc.append_basic_block('headUp')
		bodyBB = llvmFunc.append_basic_block('body')
		stepBB = llvmFunc.append_basic_block('step')
		# TODO: think about implementing an 'else' block, that gets called when the loop does not get executed
		mergeBB = llvmFunc.append_basic_block('merge')

		self._currentBuilder.branch(headBB)

		# setup continue / break targets
		ast.breakTarget = mergeBB
		ast.continueTarget = stepBB

		# count up or down?
		b = Builder.new(headBB)
		cond = b.icmp(IPRED_SGT, step, Constant.int(step.type, 0))
		b.cbranch(cond, headUpBB, headDownBB)

		# count down check
		b = Builder.new(headDownBB)
		cond = b.icmp(IPRED_SGT, b.load(inductVar.llvmRef), stop)
		b.cbranch(cond, bodyBB, mergeBB)

		# count up check
		b = Builder.new(headUpBB)
		cond = b.icmp(IPRED_SLT, b.load(inductVar.llvmRef), stop)
		b.cbranch(cond, bodyBB, mergeBB)

		# build loop body
		self._currentBuilder = Builder.new(bodyBB)
		self._dispatch(block)

		# end loop body with branch to stepBB
		self._currentBuilder.branch(stepBB)

		# now increment inductVar and branch back to head for another round
		b = Builder.new(stepBB)
		r = b.add(b.load(inductVar.llvmRef), step)
		b.store(r, inductVar.llvmRef)
		b.branch(headBB)

		# done! continue outside loop body
		self._currentBuilder = Builder.new(mergeBB)


	def _onWhile(self, ast, expression, block):

		# create blocks
		llvmFunc = self._findCurrentFunction().llvmRef
		headBB = llvmFunc.append_basic_block('head')
		bodyBB = llvmFunc.append_basic_block('body')
		mergeBB = llvmFunc.append_basic_block('merge')

		# branch to headBB / enter loop
		self._currentBuilder.branch(headBB)

		# create test
		self._currentBuilder = Builder.new(headBB)
		self._dispatch(expression)
		self._currentBuilder.cbranch(expression.llvmValue, bodyBB, mergeBB)

		# build body
		self._currentBuilder = Builder.new(bodyBB)
		ast.breakTarget = mergeBB
		ast.continueTarget = headBB

		self._dispatch(block)

		self._currentBuilder.branch(headBB)

		# continue with mergeBB
		self._currentBuilder = Builder.new(mergeBB)


	def _onBreak(self, ast):
		target = None
		for n in reversed(self._nodes):
			if hasattr(n, 'breakTarget'):
				target = n.breakTarget
				break

		assert(target and 'type checker should make sure that there is a break target')

		self._currentBuilder.branch(target)


	def _onContinue(self, ast):
		target = None
		for n in reversed(self._nodes):
			if hasattr(n, 'continueTarget'):
				target = n.continueTarget
				break

		assert(target and 'type checker should make sure that there is a break target')

		self._currentBuilder.branch(target)


	def _onPass(self, ast):
		pass

	def _onIntegerConstant(self, ast, value, suffix):
		ast.llvmValue = Constant.int(ast.esType.toLLVMType(), value)



	def _onFloatConstant(self, ast, value, suffix):
		ast.llvmValue = Constant.real(ast.esType.toLLVMType(), str(value))


	def _onStringConstant(self, ast, constant):
		# FIXME
		s = constant.text
		assert(s.startswith('ar"'))
		s = s[3:-1]


		stringConst = Constant.stringz(s)
		string = self._module.add_global_variable(stringConst.type, 'internalStringConstant')
		string.initializer = stringConst
		string.global_constant = True
		string.linkage = LINKAGE_INTERNAL

		word = self._findSymbol(name=u'word', type_=ESType).toLLVMType()
		idx = [Constant.int(word, 0), Constant.int(word, 0)]
		ast.llvmValue = string.gep(idx)



	def _onVariable(self, ast, variableName):
		# first try to find a function (which resolves to it's address), then a normal variable
		flist = self._findSymbol(fromTree=variableName, type_=ESFunction, mayFail=True)
		if flist:
			if len(flist) > 1:
				self._raiseException(RecoverableCompileError, tree=variableName, inlineText='taking the address of a overloaded function is not implemented, yet')

			f = flist[0]
			ast.llvmValue = f.llvmRef
			ast.llvmRef = f.llvmRef
		else:
			var = self._findSymbol(fromTree=variableName, type_=ESVariable)
			ast.llvmValue = self._currentBuilder.load(var.llvmRef)
			ast.llvmRef = var.llvmRef




	def _createAllocaForVar(self, name, llvmType, value=None):
		# FIXME
		if llvmType.kind == TYPE_INTEGER:
			defaultValue = Constant.int(llvmType, 0)
		elif llvmType.kind in [TYPE_FLOAT, TYPE_DOUBLE]:
			defaultValue = Constant.real(llvmType, 0)
		elif llvmType.kind == TYPE_POINTER:
			defaultValue = Constant.null(llvmType)
		elif llvmType.kind == TYPE_STRUCT:
			defaultValue= Constant.null(llvmType)
		else:
			assert(0 and 'unsupported variable type')

		if value == None:
			value = defaultValue

		# use the usual LLVM pattern to create mutable variables: use alloca
		# important: the mem2reg pass is limited to analyzing the entry block of functions,
		# so all variables must be defined there
		llvmFunc = self._findCurrentFunction().llvmRef

		entryBB = llvmFunc.get_entry_basic_block()
		entryBuilder = Builder.new(entryBB)
		entryBuilder.position_at_beginning(entryBB)
		ref = entryBuilder.alloca(llvmType, name)
		entryBuilder.store(value, ref)

		return ref


	def _onDefVariable(self, ast, variableName, typeName):
		var = self._findSymbol(fromTree=variableName, type_=ESVariable)
		var.llvmRef = self._createAllocaForVar(variableName.text, var.esType.toLLVMType())

		if self._debugMode:
			# first find reference to dbgSubProg / enclosing function ast node
			dbgSubProg = None
			for n in reversed(self._nodes):
				if hasattr(n, 'dbgSubProg'):
					dbgSubProg = n.dbgSubProg
					break

			assert(dbgSubProg and '_onDefVariable works only inside functions')

			self._debugInfoBuilder.addLocalVariableInfo(module=self._module, builder=self._currentBuilder, llvmRef=var.llvmRef, esType=var.esType, subprogram=dbgSubProg, name=variableName.text, lineNumber=variableName.line, varType='auto')


	def _onDefGlobal(self, ast, variableName, typeName, expression):
		var = self._findSymbol(fromTree=variableName, type_=ESVariable)
		llvmType = var.toLLVMType()
		mangledName = var.mangleName() # FIXME use name mangling!
		var.llvmRef = self._module.add_global_variable(llvmType, mangledName)
		llvmRef = var.llvmRef
		#llvmRef.linkage = LINKAGE_COMMON

		if typeName:
			llvmRef.initializer = Constant.null(llvmType)
		else:
			try:
				self._dispatch(expression)
				llvmRef.initializer = expression.llvmValue
			except AttributeError, ae:
				assert('_currentBuilder' in str(ae)) # TODO replace with check based on AST

				self._raiseException(RecoverableCompileError, tree=expression, inlineText='expected trivial constant expression')



	def _onCallFunc(self, ast, calleeName, expressions):
		params = []
		for x in expressions:
			self._dispatch(x)
			params.append(x.llvmValue)


		esFunction = ast.esFunction
		llvmFunc = getattr(esFunction, 'llvmRef', None)
		if not llvmFunc:
			# try to find function in this module
			try:
				llvmFunc = self._module.get_function_named(esFunction.mangledName)
			except LLVMException:
				llvmFunc = None

			if not llvmFunc:
				# was callee a function pointer?
				esVariable = self._findSymbol(fromTree=calleeName, type_=ESVariable, mayFail=True)
				if esVariable:
					llvmFunc = self._currentBuilder.load(esVariable.llvmRef)
				else:
					# function was not declared, yet...
					llvmFunc = self._module.add_function(esFunction.esType.toLLVMType(), esFunction.mangledName)
		ast.llvmValue = self._currentBuilder.call(llvmFunc, params)



	def _onBasicOperator(self, ast, op, arg1, arg2):
		tt = TreeType

		# arg1 is always valid, arg2 may be None
		self._dispatch(arg1)
		if arg2:
			self._dispatch(arg2)


		if op == tt.PLUS:
			if arg2:
				ast.llvmValue = self._currentBuilder.add(arg1.llvmValue, arg2.llvmValue)
			else:
				ast.llvmValue = arg1.llvmValue
		elif op == tt.MINUS:
			if arg2:
				ast.llvmValue = self._currentBuilder.sub(arg1.llvmValue, arg2.llvmValue)
			else:
				ast.llvmValue = self._currentBuilder.sub(Constant.null(arg1.llvmValue.type), arg1.llvmValue)
		elif op == tt.STAR:
			ast.llvmValue = self._currentBuilder.mul(arg1.llvmValue, arg2.llvmValue)
		elif op == tt.SLASH:
			if arg1.esType.isSignedInteger():
				ast.llvmValue = self._currentBuilder.sdiv(arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isUnsignedInteger():
				ast.llvmValue = self._currentBuilder.udiv(arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isFloatingPoint():
				ast.llvmValue = self._currentBuilder.fdiv(arg1.llvmValue, arg2.llvmValue)
			else:
				raise NotImplementedError('FIXME? TODO?')
		elif op == tt.PERCENT:
			if arg1.esType.isSignedInteger():
				ast.llvmValue = self._currentBuilder.srem(arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isUnsignedInteger():
				ast.llvmValue = self._currentBuilder.urem(arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isFloatingPoint():
				ast.llvmValue = self._currentBuilder.frem(arg1.llvmValue, arg2.llvmValue)
			else:
				raise NotImplementedError('TODO')
		elif op == tt.NOT:
			ast.llvmValue = self._currentBuilder.not_(arg1.llvmValue)
		elif op == tt.AND:
			ast.llvmValue = self._currentBuilder.and_(arg1.llvmValue, arg2.llvmValue)
		elif op == tt.OR:
			ast.llvmValue = self._currentBuilder.or_(arg1.llvmValue, arg2.llvmValue)
		elif op == tt.XOR:
			ast.llvmValue = self._currentBuilder.xor(arg1.llvmValue, arg2.llvmValue)
		elif op in [tt.LESS, tt.LESSEQUAL, tt.EQUAL, tt.NOTEQUAL, tt.GREATEREQUAL, tt.GREATER]:

			if arg1.esType.isSignedInteger() and arg2.esType.isSignedInteger():
				preds = {}
				preds[tt.LESS] = IPRED_SLT
				preds[tt.LESSEQUAL] = IPRED_SLE
				preds[tt.EQUAL] = IPRED_EQ
				preds[tt.NOTEQUAL] = IPRED_NE
				preds[tt.GREATEREQUAL] = IPRED_SGE
				preds[tt.GREATER] = IPRED_SGT

				ast.llvmValue = self._currentBuilder.icmp(preds[op], arg1.llvmValue, arg2.llvmValue)
			elif (arg1.esType.isUnsignedInteger() and arg2.esType.isUnsignedInteger()) or (arg1.esType.isPointer() and arg2.esType.isPointer()):
				preds = {}
				preds[tt.LESS] = IPRED_ULT
				preds[tt.LESSEQUAL] = IPRED_ULE
				preds[tt.EQUAL] = IPRED_EQ
				preds[tt.NOTEQUAL] = IPRED_NE
				preds[tt.GREATEREQUAL] = IPRED_UGE
				preds[tt.GREATER] = IPRED_UGT

				ast.llvmValue = self._currentBuilder.icmp(preds[op], arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isBoolean() and arg2.esType.isBoolean():
				preds = {}
				preds[tt.EQUAL] = IPRED_EQ
				preds[tt.NOTEQUAL] = IPRED_NE

				ast.llvmValue = self._currentBuilder.icmp(preds[op], arg1.llvmValue, arg2.llvmValue)
			elif arg1.esType.isFloatingPoint() and arg2.esType.isFloatingPoint():
				# TODO think about ordered and unordered comparisions...
				# for now ordered
				preds = {}
				preds[tt.LESS] = RPRED_OLT
				preds[tt.LESSEQUAL] = RPRED_OLE
				preds[tt.EQUAL] = RPRED_OEQ
				preds[tt.NOTEQUAL] = RPRED_ONE
				preds[tt.GREATEREQUAL] = RPRED_OGE
				preds[tt.GREATER] = RPRED_OGT
				ast.llvmValue = self._currentBuilder.fcmp(preds[op], arg1.llvmValue, arg2.llvmValue)
			else:
				print arg1.esType, arg2.esType
				raise NotImplementedError('TODO')

		elif op == tt.DOUBLESTAR:
			if arg2.llvmValue.type.kind == TYPE_INTEGER:
				# powi
				powiFunc = Function.intrinsic(self._module, INTR_POWI, [arg1.llvmValue.type])
				ast.llvmValue = self._currentBuilder.call(powiFunc, [arg1.llvmValue, arg2.llvmValue])
			else:
				# pow
				raise NotImplementedError('TODO')
		else:
			raise NotImplementedError('operator not implemented: %s / "%s"' % (op, ast.text))



	def _simpleAssignment(self, var, llvmValue):
		if not hasattr(var, 'llvmRef'):
			# does not have an associated alloca, yet
			# we MUST NOT pass a value to _createAllocaForVar! That value is not available in the entry BB!
			var.llvmRef = self._createAllocaForVar(var.name, var.esType.toLLVMType())
			if self._debugMode:
				# first find reference to dbgSubProg / enclosing function ast node
				dbgSubProg = None
				for n in reversed(self._nodes):
					if hasattr(n, 'dbgSubProg'):
						dbgSubProg = n.dbgSubProg
						break

				assert(dbgSubProg and '_onDefVariable works only inside functions')

				self._debugInfoBuilder.addLocalVariableInfo(module=self._module, builder=self._currentBuilder, llvmRef=var.llvmRef, esType=var.esType, subprogram=dbgSubProg, name=var.name, lineNumber=0, varType='auto') # FIXME fix line number


		self._currentBuilder.store(llvmValue, var.llvmRef)


	def _onAssign(self, ast, assigneeExpr, expression):
		self._dispatch(expression)

		# FIXME
		if assigneeExpr.type == TreeType.VARIABLE:
			variableName = assigneeExpr.children[0]
			var = self._findSymbol(fromTree=variableName, type_=ESVariable)
			self._simpleAssignment(var, expression.llvmValue)
		elif assigneeExpr.type == TreeType.DEREFERENCE:
			self._dispatch(assigneeExpr)

			#variableName = assigneeExpr.children[0]
			#var = self._findSymbol(fremTree=variableName, type_=ESVariable)

			self._currentBuilder.store(expression.llvmValue, assigneeExpr.llvmRef)
		else:
			assert(0 and 'FIXME? TODO?')


	def _onListAssign(self, ast, variableNames, expressions):
		# use a very simple aproach:
		# copy source variables into temporary variables
		# copy data from temporary variables to destination variables
		# this avoids difficult cases like: a,b = b,a or a,b,c = b,b,b
		# but a,b = c,d is a bit slower - but the optimizer should transform that to an efficient version

		# copy source -> temp
		temps = []
		n = len(variableNames)
		assert(n == len(expressions))
		for i in range(n):
			self._dispatch(expressions[i])

			ref = self._currentBuilder.alloca(expressions[i].esType.toLLVMType(), u'listassign_tmp')
			self._currentBuilder.store(expressions[i].llvmValue, ref)

			esVar = ESVariable(u'listassign_tmp', '__local', '__local', expressions[i].esType) # TODO insert real pkg / module names
			esVar.llvmRef = ref
			temps.append(esVar)

		# copy temp -> destination
		# this is a simple assignment
		for i in range(n):
			if variableNames[i].type == TreeType.VARIABLE:
				var = self._findSymbol(fromTree=variableNames[i].children[0], type_=ESVariable)
				value = self._currentBuilder.load(temps[i].llvmRef)
				self._simpleAssignment(var, value)
			else:
				assert(0 and 'TODO')


	def _onCast(self, ast, expression, typeName):
		self._dispatch(expression)

		bool = self._findSymbol(name=u'bool', type_=ESType)

		targetT = ast.esType
		sourceT = expression.esType

		if targetT.isEquivalentTo(sourceT, True):# may be really the same or only structurally
			# FIXME TODO is this correct???
			ast.llvmValue = expression.llvmValue
			return


		bad = False

		if targetT.isEquivalentTo(bool, False):
			if sourceT.isSignedInteger() or sourceT.isUnsignedInteger():
				ast.llvmValue = self._currentBuilder.icmp(IPRED_NE, expression.llvmValue, Constant.int(expression.llvmValue.type, 0))
			elif sourceT.isFloatingPoint():
				# TODO think about ordered and unordered
				# for now use ordered
				ast.llvmValue = self._currentBuilder.fcmp(RPRED_ONE, expression.llvmValue, Constant.real(expression.llvmValue.type, '0'))
			else:
				bad = True
		elif targetT.isSignedInteger():
			if sourceT.isEquivalentTo(bool, False):
				ast.llvmValue = self._currentBuilder.zext(expression.llvmValue, targetT.toLLVMType())
			elif sourceT.isSignedInteger():
				t = targetT.toLLVMType()
				s = sourceT.toLLVMType()

				tBits = t.width
				sBits = s.width

				if sBits > tBits:
					ast.llvmValue = self._currentBuilder.trunc(expression.llvmValue, t)
				elif sBits < tBits:
					ast.llvmValue = self._currentBuilder.sext(expression.llvmValue, t)
				else:
					assert(0 and 'dead code path; should have been caught by other checks!')
			elif sourceT.isFloatingPoint():
				ast.llvmValue = self._currentBuilder.fptosi(expression.llvmValue, targetT.toLLVMType())
			else:
				bad = True
		elif targetT.isUnsignedInteger():
			if sourceT.isEquivalentTo(bool, False):
				bad = True # FIXME
			elif sourceT.isUnsignedInteger():
				t = targetT.toLLVMType()
				s = sourceT.toLLVMType()

				tBits = t.width
				sBits = s.width

				if sBits > tBits:
					ast.llvmValue = self._currentBuilder.trunc(expression.llvmValue, t)
				elif sBits < tBits:
					ast.llvmValue = self._currentBuilder.zext(expression.llvmValue, t)
				else:
					assert(0 and 'dead code path; should have been caught by other checks!')

			elif sourceT.isSignedInteger():
				t = targetT.toLLVMType()
				s = sourceT.toLLVMType()

				tBits = t.width
				sBits = s.width

				if sBits > tBits:
					raise NotImplementedError()
				elif sBits < tBits:
					ast.llvmValue = self._currentBuilder.sext(expression.llvmValue, t)
				else:
					# FIXME???
					ast.llvmValue = expression.llvmValue
			else:
				bad = True
		elif targetT.isFloatingPoint():
			if sourceT.isSignedInteger():
				ast.llvmValue = self._currentBuilder.sitofp(expression.llvmValue, targetT.toLLVMType())
			elif sourceT.isUnsignedInteger():
				ast.llvmValue = self._currentBuilder.uitofp(expression.llvmValue, targetT.toLLVMType())
			else:
				bad = True
		elif targetT.isPointer():
			if sourceT.isPointer():
				ast.llvmValue = self._currentBuilder.bitcast(expression.llvmValue, targetT.toLLVMType())
				#ast.llvmValue = expression.llvmValue
			else:
				bad = True
		else:
			bad = True


		if bad:
			raise NotImplementedError('cast from %s to %s is not yet supported' % (sourceT, targetT))


	def _onDereference(self, ast, expression, indexExpression):
		self._dispatch(expression)

		# we have a problem: The derefencing is ambiguous
		# either we want to load a value from memory --> we need ast.llvmValue
		# or we want to store a value to memory --> we need ast.llvmRef
		# when storing data to memory the load is wasteful - but it's result never get's used
		# so the optimizer will remove it
		# for now stay stay with the inefficient code...

		word = self._findSymbol(name=u'word', type_=ESType).toLLVMType()

		esType = expression.esType
		if esType.isPointer():
			if indexExpression:
				self._dispatch(indexExpression)

				if indexExpression.llvmValue.type != word:
					llvmValue = indexExpression.llvmValue
					llvmType = llvmValue.type

					if llvmType.kind != TYPE_INTEGER:
						self._raiseException(RecoverableCompileError, tree=indexExpression, inlineText='index type must be integer')

					if llvmType.width == 32 and word.width == 64:
						llvmValue = self._currentBuilder.sext(llvmValue, word)
					elif llvmType.width == 64 and word.width == 32:
						self._raise(RecoverableCompileError, tree=indexExpression, inlineText='the target architecture only supports 32 bit indices')
					else:
						assert(0 and 'FIXME or should this never happen --> dead code path?')
				else:
					llvmValue = indexExpression.llvmValue


				idx = [llvmValue]
			else:
				idx = [Constant.int(word, 0)]

			toDeref = expression.llvmValue
		elif esType.isStruct():
			if indexExpression.type == TreeType.NAME:
				memberIdx = esType.getStructMemberIndexByName(indexExpression.text)
				idx = [Constant.int(word, 0), Constant.int(Type.int(32), memberIdx)]
			else:
				raise NotImplementedError('TODO')

			toDeref = expression.llvmRef
		else:
			assert(0 and 'dead code path')

		# every variable is an alloca --> first get the real memory address
		realAddrWithOffset = self._currentBuilder.gep(toDeref, idx)
		ast.llvmRef = realAddrWithOffset

		# now load data from it
		ast.llvmValue = self._currentBuilder.load(realAddrWithOffset)



	def _onAlias(self, ast, name, typeName):
		pass


	def _onTypedef(self, ast, name, typeName):
		pass


	def _onAddressOf(self, ast, expression):
		self._dispatch(expression)

		# see _onDereference for the ambigous use of this instruction


		ast.llvmRef = expression.llvmRef
		ast.llvmValue = expression.llvmRef


	def _onNew(self, ast, typeName, numExpr):
		if numExpr:
			self._dispatch(numExpr)
			numElements = numExpr.llvmValue
		else:
			numElements = Constant.int(Type.int(32), 1)


		ast.llvmValue = self._currentBuilder.malloc_array(ast.esType.dereference().toLLVMType(), numElements)


	def _onDefStruct(self, ast, name, members):
		self._module.add_type_name(name.text, ast.esType.toLLVMType())


	def _onNoneConstant(self, ast):
		ast.llvmValue = Constant.null(Type.pointer(Type.int(8)))



	def _onBooleanConstant(self, ast, value):
		ast.llvmValue = Constant.int(Type.int(1), value)


	def walkAST(self, ast, absFilename, sourcecode='', debugMode=False):
		assert(ast.type == TreeType.MODULESTART)

		self._module = None
		self._debugMode = debugMode
		astwalker.ASTWalker.walkAST(self, ast, absFilename, sourcecode)

		self._module.verify()

		return self._module






def run(module, function):
	mp = ModuleProvider.new(module)
	ee = ExecutionEngine.new(mp)

	return ee.run_function(function, [])



