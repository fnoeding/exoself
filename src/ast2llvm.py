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

from mangle import *
from esfunction import ESFunction
from esvalue import ESValue
from esvariable import ESVariable
from estype import ESType
from errors import *
import astwalker
from tree import Tree, TreeType
import typeannotator






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

		try:
			flist = self._findSymbol(name=u'main', type_=ESFunction)
		except CompileError:
			flist = []

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
				b.branch(BB)

				b = Builder.new(BB)
				r = b.call(esMain.llvmRef, [])

				retTypes = esMain.esType.getFunctionReturnTypes()
				assert(len(retTypes) == 1)

				if retTypes[0].toLLVMType() != Type.void():
					b.ret(r)
				else:
					b.ret(Constant.int(Type.int(32), 0))
			else:
				# TODO implement version with parameters
				self._raiseException(RecoverableCompileError, postText=s)



	def _onModuleStart(self, ast, packageName, moduleName, statements):
		self._errors = 0
		self._warnings = 0

		self._module = Module.new(ast.moduleName)
		self._moduleNode = ast

		# add some helper functions / prototypes / ... to the module
		self._addHelperFunctionsPreTranslation()

		# translate
		for x in statements:
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


		# finally add some more helper functions / prototypes / ... to the module
		self._addHelperFunctionsPostTranslation()



	def _onImportAll(self, ast, moduleName):
		pass



	def _onDefFunction(self, ast, modifierKeys, modifierValues, name, returnTypeName, parameterNames, parameterTypeNames, block):
		esFunction = ast.esFunction
		esType = esFunction.esType

		if esFunction.name == 'main':# a user defined main gets called by a compiler defined main function
			mangledName = '__ES_main'
		elif modMangling == 'C':
			mangledName = esFunction.name
		else:
			mangledName = mangleFunction(esFunction.package, esFunction.module, esFunction.name,
					['void'], # FIXME
					[]) #FIXME

		try:
			# make really sure there is no function with this name
			if self._module.get_function_named(mangledName):
				nameUsed = True
		except:
			nameUsed = False
		if nameUsed:
			s1 = 'mangled name already in use: %s' % mangledName
			s2 ='internal compiler error: name mangling probably not working correctly. Please submit bug report.'
			self._raiseException(CompileError, tree=tree.getChild(1), inlineText=s1, postText=s2)


		llvmRef = self._module.add_function(esType.toLLVMType(), mangledName)
		esFunction.llvmRef = llvmRef

		# set parameter names
		for i,x in enumerate(parameterNames):
			llvmFunc.args[i].name = x.text


		if not block:
			# only a prototype
			return

	
		entryBB = llvmRef.append_basic_block('entry')
		bEntry = Builder.new(entryBB)


		# add variables
		# TODO
		#	for i in range(len(func.llvmFunc.args)):
		#		self._createAllocaForVar(unicode(func.llvmFunc.args[i].name), func.llvmFunc.args[i].type, func.paramTypes[i].typename, func.llvmFunc.args[i], treeForErrorReporting=tree)

		bb = llvmRef.append_basic_block('bb')
		bEntry.branch(bb)

		self._currentBuilder = Builder.new(bb)
		self._dispatch(block)

		returnTypes = esFunction.esType.getFunctionReturnTypes()
		if len(returnTypes) == 1 and returnTypes[0].toLLVMType() == Type.void():
			self._currentBuilder.ret_void()
		else:
			bb = self._currentBuilder.block
			if not (bb.instructions and bb.instructions[-1].is_terminator):
				s = self._generateContext(preText='warning:', postText='control flow possibly reaches end of non-void function. Inserting trap instruction...', lineBase1=block.line, numAfter=3)
				print s
				trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
				self._currentBuilder.call(trapFunc, [])
				self._currentBuilder.ret(Constant.int(Type.int(32), -1)) # and return, otherwise func.verify will fail
				
				

		llvmRef.verify()


	def _onBlock(self, ast, blockContent):
		for x in blockContent:
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

	def _onAssert(self, tree):
		assert(tree.text == 'assert')

		# TODO add a compiler switch to disable asserts, so they become noop's
		# TODO add a compiler switch to disable inclusion of context data

		value = self._dispatch(tree.getChild(0))
		cond = self._currentBuilder.icmp(IPRED_EQ, value.llvmValue, Constant.int(value.llvmType, 0))

		# if value is statically available bail out now / warn
		# this does not work... investigate later
		#if value == Constant.int(Type.int(1), 0):
		#	print 'assert is always False in %s:%d' % ('???', tree.getLine())

		# now implement an if

		thenBB = self._currentFunction.llvmFunc.append_basic_block('assert_true') # trap path
		elseBB = self._currentFunction.llvmFunc.append_basic_block('assert_false') # BasicBlock(None) # TODO check if this is really ok

		self._currentBuilder.cbranch(cond, thenBB, elseBB)


		thenBuilder = Builder.new(thenBB)

		# build error string
		if tree.line:
			errorStringConst = 'assert failed! file %s line %d:\n' % (self._filename, tree.line)

			start = max(tree.line - 1 - 5, 0)
			stop = min(tree.line - 1 + 1, len(self._sourcecodeLines))
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

		idx = [Constant.int(Type.int(32), 0), Constant.int(Type.int(32), 0)]
		errorStringGEP = errorString.gep(idx)
		puts = self._module.get_function_named('puts')
		thenBuilder.call(puts, [errorStringGEP])

		# emit abort
		abortFunc = self._module.get_function_named('abort')
		thenBuilder.call(abortFunc, [])
		thenBuilder.branch(elseBB) # we'll never get here - but create proper structure of IR
	
		self._currentBuilder = Builder.new(elseBB)

	def _onIf(self, tree):
		assert(tree.text == 'if')
		# children: expr block (expr block)* block?
		#           if         else if       else
		
		mergeBB = self._currentFunction.llvmFunc.append_basic_block('if_merge')
		# iterate over all 'if' and 'else if' blocks
		for i in range(tree.getChildCount() // 2):
			condESValue = self._dispatch(tree.getChild(2 * i))
			if condESValue.llvmType != Type.int(1):# FIXME use comparison against bool?
				cond = self._currentBuilder.icmp(IPRED_NE, condESValue.llvmValue, Constant.int(condESValue.llvmType, 0)) # FIXME use conversion to bool
			else:
				cond = condESValue.llvmValue

			
	
			thenBB = self._currentFunction.llvmFunc.append_basic_block('if_then')
			elseBB = self._currentFunction.llvmFunc.append_basic_block('if_else')

			self._currentBuilder.cbranch(cond, thenBB, elseBB)

			# generate code for then branch
			self._currentBuilder = Builder.new(thenBB)
			self._dispatch(tree.getChild(2 * i + 1))

			# branch to mergeBB, but only if there was no terminator instruction
			currentBB = self._currentBuilder.block
			if not (currentBB.instructions and currentBB.instructions[-1].is_terminator):
				self._currentBuilder.branch(mergeBB)

			# continue with next else if / else
			self._currentBuilder = Builder.new(elseBB)
		if tree.getChildCount() % 2 == 1:
			# generate code for else branch
			self._dispatch(tree.getChild(tree.getChildCount() - 1))

		# close last elseBB, but only if there was no terminator instruction
		currentBB = self._currentBuilder.block
		if not (currentBB.instructions and currentBB.instructions[-1].is_terminator):
			self._currentBuilder.branch(mergeBB)

		# continue in mergeBB
		self._currentBuilder = Builder.new(mergeBB)
		

	def _onFor(self, tree):
		assert(tree.text == 'for')

		loopVarName = tree.getChild(0).text
		loopBody = tree.getChild(2)
		loopExpression = tree.getChild(1)
		assert(loopExpression.text == 'range')
		assert(1 <= loopExpression.getChildCount() <= 3)
		n = loopExpression.getChildCount()

		with ScopeStackWithProxy(self._scopeStack):
			inductVar = self._scopeStack.find(loopVarName)
			if inductVar:
				assert(inductVar.llvmType.pointee == Type.int(32)) # 'range' expects some kind of integer...
			else:
				inductVar = self._createAllocaForVar(loopVarName, Type.int(32), u'int32')# FIXME determine types from range!
			start = ESValue(Constant.int(inductVar.llvmType.pointee, 0), inductVar.typename)
			step = ESValue(Constant.int(inductVar.llvmType.pointee, 1), inductVar.typename)

			# TODO emit warnings if range would overflow induct var type

			if n == 1:
				stop = self._dispatch(loopExpression.getChild(0))
			elif n == 2:
				start = self._dispatch(loopExpression.getChild(0))
				stop = self._dispatch(loopExpression.getChild(1))
			elif n == 3:
				start = self._dispatch(loopExpression.getChild(0))
				stop = self._dispatch(loopExpression.getChild(1))
				step = self._dispatch(loopExpression.getChild(2))

			# convert types
			if stop.typename != inductVar.typename:
				stop = self._convertType(stop, inductVar.typename)
			if step.typename != inductVar.typename:
				step = self._convertType(step, inductVar.typename)
			if start.typename != inductVar.typename:
				start = self._convertType(start, inductVar.typename)

			# setup loop by initializing induction variable
			self._currentBuilder.store(start.llvmValue, inductVar.llvmRef)

			# create blocks
			headBB = self._currentFunction.llvmFunc.append_basic_block('head') # decide between Up and Down
			headDownBB = self._currentFunction.llvmFunc.append_basic_block('headDown')
			headUpBB = self._currentFunction.llvmFunc.append_basic_block('headUp')
			bodyBB = self._currentFunction.llvmFunc.append_basic_block('body')
			stepBB = self._currentFunction.llvmFunc.append_basic_block('step')
			# TODO: think about implementing an 'else' block, that gets called when the loop does not get executed
			mergeBB = self._currentFunction.llvmFunc.append_basic_block('merge')

			self._currentBuilder.branch(headBB)

			# count up or down?
			b = Builder.new(headBB)
			cond = b.icmp(IPRED_SGT, step.llvmValue, Constant.int(step.llvmType, 0))
			b.cbranch(cond, headUpBB, headDownBB)

			# count down check
			b = Builder.new(headDownBB)
			cond = b.icmp(IPRED_SGT, b.load(inductVar.llvmRef), stop.llvmValue)
			b.cbranch(cond, bodyBB, mergeBB)

			# count up check
			b = Builder.new(headUpBB)
			cond = b.icmp(IPRED_SLT, b.load(inductVar.llvmRef), stop.llvmValue)
			b.cbranch(cond, bodyBB, mergeBB)

			# build loop body
			self._currentBuilder = Builder.new(bodyBB)
			self._breakTargets.append(mergeBB)
			self._continueTargets.append(stepBB)
			try:
				self._dispatch(loopBody)
			finally:
				self._breakTargets.pop()
				self._continueTargets.pop()

			# end loop body with branch to stepBB
			self._currentBuilder.branch(stepBB)

			# now increment inductVar and branch back to head for another round
			b = Builder.new(stepBB)
			r = b.add(b.load(inductVar.llvmRef), step.llvmValue)
			b.store(r, inductVar.llvmRef)
			b.branch(headBB)

			# done! continue outside loop body
			self._currentBuilder = Builder.new(mergeBB)


	def _onWhile(self, tree):
		assert(tree.text == 'while')


		with ScopeStackWithProxy(self._scopeStack):
			# create blocks
			headBB = self._currentFunction.llvmFunc.append_basic_block('head')
			bodyBB = self._currentFunction.llvmFunc.append_basic_block('body')
			# TODO think about an else block which gets executed iff the body is not executed at least once
			mergeBB = self._currentFunction.llvmFunc.append_basic_block('merge')

			# branch to headBB / enter loop
			self._currentBuilder.branch(headBB)

			# create test
			self._currentBuilder = Builder.new(headBB)
			loopExpr = self._dispatch(tree.getChild(0))
			if loopExpr.llvmType != Type.int(1):# FIXME use typenames?
				# FIXME use conversion to bool
				loopExpr = ESValue(self._currentBuilder.icmp(IPRED_NE, loopExpr.llvmValue, 0), u'bool')

			self._currentBuilder.cbranch(loopExpr.llvmValue, bodyBB, mergeBB)

			# build body
			self._currentBuilder = Builder.new(bodyBB)
			self._breakTargets.append(mergeBB)
			self._continueTargets.append(headBB)
			try:
				self._dispatch(tree.getChild(1))
			finally:
				self._breakTargets.pop()
				self._continueTargets.pop()

			self._currentBuilder.branch(headBB)

			# continue with mergeBB
			self._currentBuilder = Builder.new(mergeBB)


	def _onBreak(self, tree):
		assert(tree.text == 'break')

		if not self._breakTargets:
			self._raiseException(RecoverableCompileError, tree=tree, inlineText='break is only possible inside loop or switch statements')
		self._currentBuilder.branch(self._breakTargets[-1])


	def _onContinue(self, tree):
		assert(tree.text == 'continue')

		if not self._continueTargets:
			self._raiseException(RecoverableCompileError, tree=tree, inlineText='continue is only possible inside loop statements')

		self._currentBuilder.branch(self._continueTargets[-1])
		

	def _onPass(self, ast):
		pass

	def _onIntegerConstant(self, ast, constant):
		value = constant.text.replace('_', '').lower()

		if value.startswith('0x'):
			i = int(value[2:], 16)
		elif value.startswith('0b'):
			i = int(value[2:], 2)
		elif value.startswith('0') and len(value) > 1:
			i = int(value[1:], 8)
		else:
			i = int(value)

		# TODO think a bit more about default types
		signed = True # TODO
		if -(2 ** 7) <= i <= 2 ** 7 - 1:
			bits = 8
		elif -(2 ** 15) <= i <= 2 ** 15 - 1:
			bits = 16
		elif -(2 ** 31) <= i <= 2 ** 31 - 1:
			bits = 32
		elif -(2 ** 63) <= i <= 2 ** 63 - 1:
			bits = 64
		else:
			self._raiseException(RecoverableCompileError, tree=constant, inlineText='constant can not be represented by an int64')

		# FIXME TODO think about a default type. int8 is somewhat inconvenient as a default type...
		# for now just use int32 that works on every x86 / x86_64 etc.
		if bits < 32:
			bits = 32
		
		c = Constant.int(Type.int(bits), i)

		ast.llvmValue = c



	def _onFloatConstant(self, tree):
		assert(tree.text == 'FLOAT_CONSTANT')

		value = tree.getChild(0).text.replace('_', '').lower()
		
		f = float(value)

		constType = Type.float()

		return Constant.real(constType, f) # FIXME use float


	def _onVariable(self, tree):
		assert(tree.text == 'VARIABLE')

		varName = tree.getChild(0).text
		var = self._scopeStack.find(varName)
		if not var:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='undefined variable name')

		return ESValue(self._currentBuilder.load(var.llvmRef), var.typename) # FIXME use real type!


	def _createAllocaForVar(self, name, llvmType, typename, value=None, treeForErrorReporting=None):
		assert(not isinstance(llvmType, str) and not isinstance(llvmType, unicode))
		assert(isinstance(typename, unicode))

		# FIXME
		if llvmType.kind == TYPE_INTEGER:
			defaultValue = Constant.int(llvmType, 0)
		else:
			assert(0 and 'unsupported variable type')

		if value == None:
			value = defaultValue

		# check if this variable is already defined
		if self._scopeStack.find(name):
			self._raiseException(RecoverableCompileError, tree=treeForErrorReporting, inlineText='variable already defined: %s' % name)

		# use the usual LLVM pattern to create mutable variables: use alloca
		# important: the mem2reg pass is limited to analyzing the entry block of functions,
		# so all variables must be defined there

		entryBB = self._currentFunction.llvmFunc.get_entry_basic_block()
		entryBuilder = Builder.new(entryBB)
		# workaround: llvm-py segfaults when we call position_at_beginning on an empty block
		if entryBB.instructions:
			entryBuilder.position_at_beginning(entryBB)
		ref = entryBuilder.alloca(llvmType, name)
		entryBuilder.store(value, ref)

		var = ESVariable(ref, typename, name)

		self._scopeStack.add(name, var)

		return var


	def _onDefVariable(self, tree):
		assert(tree.text == 'DEFVAR')

		varName = tree.getChild(0).text
		varType = tree.getChild(1).text

		raiseUnknownType = (lambda: self._raiseException(RecoverableCompileError, tree=tree.getChild(1), inlineText='unknown type'))
		if varType.startswith('int') and varType[3].isdigit():
			numBits = int(varType[3:])

			if numBits not in [8, 16, 32, 64]:
				raiseUnknownType()
				

			llvmType = Type.int(numBits)
		else:
			raiseUnknownType()

		self._createAllocaForVar(varName, llvmType, varType, treeForErrorReporting=tree.getChild(0))


	def _onCallFunc(self, tree):
		assert(tree.text == 'CALLFUNC')

		ci = _childrenIterator(tree)
		callee = ci.next().text
		nArguments = tree.getChildCount() - 1

		# find function
		functions = self._scopeStack.find(callee)
		if not functions:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='undefined function')

		# select depending on number of arguments, ignoring anything else for now
		# FIXME use ESType based checking?
		function = None
		for f in functions:
			if len(f.llvmFunc.args) == nArguments:
				function = f
				break

		if not function:
			s1 = 'no matching function found'
			s2 = ['canditates:']
			for f in functions:
				s2.append('\t%s' % f.llvmFunc.type.pointee)
			s2 = '\n'.join(s2)
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText=s1, postText=s2)


		params = []
		for x in ci:
			r = self._dispatch(x)
			params.append(r)

		# check arguments
		# TODO check against ES types!
		if len(params) != len(function.llvmFunc.args):
			s = 'function type: %s' % function.type.pointee
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='wrong number of arguments', postText=s)

		for i in range(len(function.llvmFunc.args)):
			if function.llvmFunc.args[i].type != params[i].llvmType: # FIXME use ESType based checking
				# try implicit conversion
				try:
					params[i] = self._convertType(params[i], function.paramTypes[i])
				except CompileError, NotImplementedError:
					s = 'argument %d type: %s' % (i + 1, function.llvmFunc.args[i].type)
					s2 = 'wrong argument type: %s' % params[i].llvmType
					self._raiseException(RecoverableCompileError, tree=tree.getChild(i + 1), inlineText=s2, postText=s)

		r = self._currentBuilder.call(function.llvmFunc, [x.llvmValue for x in params], 'ret_%s' % callee)
		return ESValue(r, function.returnType.typename)

	def _onBasicOperator(self, tree):
		nodeType = tree.text
		if tree.getChildCount() == 2 and nodeType in '''* ** // % / and xor or + - < <= == != >= >'''.split():
			first = tree.getChild(0)
			second = tree.getChild(1)

			v1 = self._dispatch(first)
			v2 = self._dispatch(second)


			if v1.typename != v2.typename:
				v1, v2 = self._promoteTypes(v1, v2)

			assert(v1.typename == v2.typename)


			if nodeType == '*':
				r = self._currentBuilder.mul(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType == '**':
				# FIXME we are using the floating point power instead of an integer calculation
				powiFunc = Function.intrinsic(self._module, INTR_POWI, [Type.double()])

				# FIXME FIXME FIXME FIXME FIXME
				# convert first argument to double
				b = self._currentBuilder.sitofp(v1.llvmValue, Type.double())
				if v2.typename != 'int32':
					e = self._convertType(v2, u'int32').llvmValue
				else:
					e = v2.llvmValue

				
				r = self._currentBuilder.call(powiFunc, [b, e])
				return ESValue(self._currentBuilder.fptosi(r, Type.int(32)), u'int32') # FIXME choose better types
			elif nodeType == '//':# integer division
				r = self._currentBuilder.sdiv(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType == '/':# floating point division
				# FIXME use FP div if result is not an integer
				r = self._currentBuilder.sdiv(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType == '%':
				r = self._currentBuilder.srem(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType == '+':
				r = self._currentBuilder.add(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType == '-':
				r = self._currentBuilder.sub(v1.llvmValue, v2.llvmValue)
				return ESValue(r, v1.typename)
			elif nodeType in 'and xor or'.split():
				# TODO implement short circuiting!

				# first convert parameters to booleans
				# TODO we should probably use typename and a check against bool
				if v1.llvmType != Type.int(1):
					b1 = self._currentBuilder.icmp(IPRED_NE, v1.llvmValue, Constant.int(v1.llvmType, 0))
				else:
					b1 = v1.llvmValue
				if v2.llvmType != Type.int(1):
					b2 = self._currentBuilder.icmp(IPRED_NE, v2.llvmValue, Constant.int(v2.llvmType, 0))
				else:
					b2 = v2.llvmValue
				
				# do check
				if nodeType == 'and':
					r = self._currentBuilder.and_(b1, b2)
				elif nodeType == 'xor':
					r = self._currentBuilder.xor(b1, b2)
				elif nodeType == 'or':
					r = self._currentBuilder.or_(b1, b2)
				else:
					assert(0 and 'dead code path')

				# and go back to int32
				r = self._currentBuilder.zext(r, Type.int(32)) # FIXME remove!
				return ESValue(r, u'int32')
			elif nodeType in '< <= == != >= >'.split():
				m = {}
				m['<'] = IPRED_SLT
				m['<='] = IPRED_SLE
				m['=='] = IPRED_EQ
				m['!='] = IPRED_NE
				m['>='] = IPRED_SGE
				m['>'] = IPRED_SGT
				pred = m[nodeType]
				assert(v1.llvmType == v2.llvmType and 'types did not match in comp op')

				return ESValue(self._currentBuilder.icmp(pred, v1.llvmValue, v2.llvmValue), u'bool')
			else:
				assert(0 and 'should never get here')
		elif tree.getChildCount() == 1 and nodeType in '''- + not'''.split():
			v1 = self._dispatch(tree.getChild(0))

			if nodeType == '+':
				return v1
			elif nodeType == '-':
				if v1.llvmType.kind == TYPE_INTEGER:
					r = self._currentBuilder.sub(Constant.int(v1.llvmType, 0), v1.llvmValue)
					return ESValue(r, v1.typename)
				else:
					raise NotImplementedError()
			elif nodeType == 'not':
				r = self._currentBuilder.icmp(IPRED_EQ, v1.llvmValue, Constant.int(v1.llvmType, 0))

				return ESValue(self._currentBuilder.zext(r, Type.int(32)), u'int32') # FIXME use bool
			else:
				assert(0 and 'dead code path')
		else:
			raise NotImplementedError('basic operator \'%s\' not yet implemented' % nodeType)

	def _simpleAssignment(self, name, value, treeForErrorReporting=None):
		var = self._scopeStack.find(name)
		if var:
			# something with this name exists -> check type
			if not isinstance(var, ESVariable):
				s1 = 'not a variable'
				self._raiseException(RecoverableCompileError, tree=treeForErrorReporting, inlineText=s1)

			# check type
			if value.llvmType != var.llvmType.pointee:# FIXME use typename check?
				value = self._convertType(value, var.typename)
				#s1 = 'expression is of incompatible type'
				#s2 = 'lhs type: %s; rhs type: %s' % (var.typename, value.typename)
				#self._raiseException(RecoverableCompileError, tree=treeForErrorReporting, inlineText=s1, postText=s2)
			self._currentBuilder.store(value.llvmValue, var.llvmRef)
		else:
			# new variable
			# do not pass value when creating the variable! The value is NOT available in the entry block (at least in general)!
			self._createAllocaForVar(name, value.llvmType, value.typename, treeForErrorReporting=treeForErrorReporting)

			var = self._scopeStack.find(name)
			assert(isinstance(var, ESVariable))
			self._currentBuilder.store(value.llvmValue, var.llvmRef)
		
		return var


	def _onAssign(self, tree):
		assert(tree.text == '=')
		assert(tree.getChildCount() == 2) # require desugar

		varName = tree.children[0].text
		value = self._dispatch(tree.children[1])

		self._simpleAssignment(varName, value, treeForErrorReporting=tree.children[1])


	def _onListAssign(self, tree):
		assert(tree.text == 'LISTASSIGN')

		lhs = tree.getChild(0)
		assert(lhs.text == 'ASSIGNLIST')
		rhs = tree.getChild(1)
		assert(rhs.text == 'ASSIGNLIST')

		assert(lhs.getChildCount() == rhs.getChildCount() and 'different number of assignees and expressions')
		n = rhs.getChildCount()

		# use a very simple aproach:
		# copy source variables into temporary variables
		# copy data from temporary variables to destination variables
		# this avoids difficult cases like: a,b = b,a or a,b,c = b,b,b
		# but a,b = c,d is a bit slower - but the optimizer should transform that to an efficient version

		# copy source -> temp
		temps = []
		for i in range(n):
			value = self._dispatch(rhs.getChild(i))
			ref = self._currentBuilder.alloca(value.llvmType, u'listassign_tmp')
			self._currentBuilder.store(value.llvmValue, ref)
			temps.append(ESVariable(ref, value.typename, u'listassign_tmp'))

		# copy temp -> destination
		# this is a simple assignment
		for i in range(n):
			value = self._currentBuilder.load(temps[i].llvmRef)
			destination = lhs.getChild(i).text

			self._simpleAssignment(destination, ESValue(value, temps[i].typename))




#	def _dispatch(self, tree):
#		return self._dispatchTable[tree.text](tree)



	def walkAST(self, ast, absFilename, sourcecode=''):
		assert(ast.type == TreeType.MODULESTART)

		self._module = None
		astwalker.ASTWalker.walkAST(self, ast, absFilename, sourcecode)

		self._module.verify()

		return self._module



	def _exportGloballyVisibleSymbols(self):
		assert(self._module and 'run translateAST first')

		# TODO refactor to avoid accessing details of ScopeStack

		# globally visible symbols
		d = {}
		d['package'] = self._packageName
		d['module'] = self._moduleName

		functions = []
		d['functions'] = functions

		for key, value in self._scopeStack._stack[0]._functions.items():
			for x in value:
				f = {}
				f['name'] = key
				f['mangledName'] = x.llvmFunc.name # use direct name
				f['function'] = x # FIXME use a copy here
				f['llvmType'] = x.llvmType

				functions.append(f)

		return d

	def _convertType(self, esValue, toType, warn=True):
		# TODO refactor code into external functions
		assert(isinstance(esValue, ESValue))
		if isinstance(toType, ESType):# FIXME toType should always be ESType
			toType = toType.typename
		assert(isinstance(toType, unicode))# FIXME toType should never be a string

		t1 = esValue.typename
		t2 = toType

		if t1.startswith(u'int') and t2.startswith(u'int'):
			# both are signed integers
			t1Bits = int(t1[3:])
			t2Bits = int(t2[3:])

			if t1Bits < t2Bits:
				r = self._currentBuilder.sext(esValue.llvmValue, ESTypeToLLVM(t2))
				return ESValue(r, t2)
			else:
				# this COULD lose precision
				# FIXME TODO emit a warning
				r = self._currentBuilder.trunc(esValue.llvmValue, ESTypeToLLVM(t2))
				return ESValue(r, t2)
		else:
			self._raiseException(RecoverableCompileError, postText='conversion between %s and %s is not yet supported' % (t1, t2))

	def _promoteTypes(self, v1, v2):
		t1 = v1.typename
		t2 = v2.typename

		assert(t2 != t1)

		if t1.startswith(u'int') and t2.startswith(u'int'):
			# both are signed integers
			t1Bits = int(t1[3:])
			t2Bits = int(t2[3:])

			if t1Bits < t2Bits:
				c = self._convertType(v1, t2)
				return (c, v2)
			else:
				c = self._convertType(v2, t1)
				return (v1, c)
		else:
			self._raiseException(RecoverableCompileError, postText='conversion between %s and %s is not yet supported' % (t1, t2))


	

def run(module, function):
	mp = ModuleProvider.new(module)
	ee = ExecutionEngine.new(mp)

	return ee.run_function(function, [])



