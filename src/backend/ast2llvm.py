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

def _childrenIterator(tree):
	n = tree.getChildCount()
	for i in range(n):
		yield tree.getChild(i)


class _ScopeStackWithProxy(object):
	def __init__(self, ss):
		self._ss = ss

	def __enter__(self):
		self._ss.pushScope()

	def __exit__(self, type, value, tb):
		self._ss.popScope()



class _ScopeStack(object):
	def __init__(self):
		self._stack = {0: {}}
		self._currentLevel = 0


	def popScope(self):
		assert(self._currentLevel > 0)

		del self._stack[self._currentLevel]
		self._currentLevel -= 1


	def pushScope(self):
		self._currentLevel += 1
		self._stack[self._currentLevel] = {}


	def add(self, name, ref, allowOverwriting=False):
		if not allowOverwriting:
			assert(not self.find(name))

		self._stack[self._currentLevel][name] = ref


	def find(self, name):
		for x in range(self._currentLevel, -1, -1):
			m = self._stack[x]
			try:
				return m[name]
			except:
				pass

		return None


class CompileError(Exception):
	pass

class RecoverableCompileError(CompileError):
	# just continue with next suitable AST node, for example continue with next function
	# if this error is raised compilation MUST still fail! It only allows to give the user
	# more information about further errors in the source code
	pass



class ModuleTranslator(object):
	def __init__(self):
		self._dispatchTable = {}
		self._dispatchTable['MODULE'] = self._onModule
		self._dispatchTable['IMPORTALL'] = self._onImportAll
		self._dispatchTable['DEFFUNC'] = self._onDefFunction
		self._dispatchTable['BLOCK'] = self._onBlock
		self._dispatchTable['pass'] = self._onPass
		self._dispatchTable['return'] = self._onReturn
		self._dispatchTable['assert'] = self._onAssert
		self._dispatchTable['if'] = self._onIf
		self._dispatchTable['for'] = self._onFor
		self._dispatchTable['while'] = self._onWhile
		self._dispatchTable['break'] = self._onBreak
		self._dispatchTable['continue'] = self._onContinue
		self._dispatchTable['INTEGER_CONSTANT'] = self._onIntegerConstant
		self._dispatchTable['FLOAT_CONSTANT'] = self._onFloatConstant
		self._dispatchTable['CALLFUNC'] = self._onCallFunc
		self._dispatchTable['VARIABLE'] = self._onVariable
		self._dispatchTable['DEFVAR'] = self._onDefVariable
		self._dispatchTable['+'] = self._onBasicOperator
		self._dispatchTable['-'] = self._onBasicOperator
		self._dispatchTable['*'] = self._onBasicOperator
		self._dispatchTable['**'] = self._onBasicOperator
		self._dispatchTable['/'] = self._onBasicOperator
		self._dispatchTable['//'] = self._onBasicOperator
		self._dispatchTable['%'] = self._onBasicOperator
		self._dispatchTable['not'] = self._onBasicOperator
		self._dispatchTable['and'] = self._onBasicOperator
		self._dispatchTable['or'] = self._onBasicOperator
		self._dispatchTable['xor'] = self._onBasicOperator
		self._dispatchTable['<'] = self._onBasicOperator
		self._dispatchTable['<='] = self._onBasicOperator
		self._dispatchTable['=='] = self._onBasicOperator
		self._dispatchTable['!='] = self._onBasicOperator
		self._dispatchTable['>='] = self._onBasicOperator
		self._dispatchTable['>'] = self._onBasicOperator
		self._dispatchTable['='] = self._onAssign
		self._dispatchTable['LISTASSIGN'] = self._onListAssign

	def _generateContext(self, preText, postText, inlineText='', lineBase1=0, charBase1=0, numBefore=5, numAfter=0):
		if not self._sourcecodeLines or not lineBase1:
			s = []
			if preText:
				s.append(preText)
			if inlineText:
				s.append(inlineText)
			s.append(postText)
			print s
			return '\n\t'.join(s) + '\n'


		s = []
		if preText:
			s.append(preText)

		start = max(lineBase1 - 1 - 5, 0)
		stop = min(lineBase1 - 1 + 1 + numAfter, len(self._sourcecodeLines))
		for i in range(start, stop):
			s.append('% 5d: %s' % (i + 1, self._sourcecodeLines[i]))
			if i == stop - 1:
				x = (' ' * (7 + charBase1))
				x += '^--- %s' % inlineText
				s.append(x)
		if postText:
			s.append(postText)


		return '\n'.join(s) + '\n'

	def _raiseException(self, exType, line=None, tree=None, numContextLines=5, preText='error:', postText='', inlineText=''):
		if line:
			s = self._generateContext(lineBase1=line, preText=preText, postText=postText, inlineText=inlineText)
		elif tree and tree.line:
			s = self._generateContext(lineBase1=tree.line, charBase1=tree.charPos, preText=preText, postText=postText, inlineText=inlineText)
		else:
			s = self._generateContext(preText=preText, postText=postText, inlineText=inlineText)

		raise exType(s)
		


	def _addHelperFunctions(self):
		# puts
		retType= Type.int(32)
		parameterTypes = []
		parameterTypes.append(Type.pointer(Type.int(8)))
		functionType = Type.function(retType, parameterTypes)
		self._module.add_function(functionType, 'puts')

		# abort
		functionType = Type.function(Type.void(), [])
		self._module.add_function(functionType, 'abort')



	def _onModule(self, tree):
		assert(tree.text == 'MODULE')

		self._errors = 0
		self._warnings = 0

		self._module = Module.new('main_module')
		self._scopeStack = _ScopeStack() # used to resolve variables
		self._breakTargets = [] # every loop pushes / pops basic blocks onto this stack for usage by break.
		self._continueTargets = [] # see breakTargets

		# add some helper functions / prototypes / ... to the module
		self._addHelperFunctions()

		# first pass: make all functions available, so we don't need any stupid forward declarations
		for x in _childrenIterator(tree):
			try:
				if x.text == 'DEFFUNC':
					self._onDefProtoype(x)
			except RecoverableCompileError, e:
				print e.message.rstrip()
				self._errors += 1
			except CompileError, e:
				print e.message.rstrip()
				self._errors += 1
				break

		if self._errors:
			raise CompileError('errors occured during checking global statements: aborting')


		# second pass: translate code
		for x in _childrenIterator(tree):
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

	def _onImportAll(self, tree):
		assert(tree.text == 'IMPORTALL')
		assert(os.path.isabs(self._filename)) # also checkd in translateAST, but be really sure

		modPath = tree.getChild(0).text	
		if modPath.startswith('.'):
			modPath = modPath.split('.')
			if modPath[0] == '':
				modPath.pop(0)
			
			path, ignored = os.path.split(self._filename)
			for i in range(len(modPath)):
				if modPath[i] != '':
					break

				path, ignored = os.path.split(path)
			toImport = os.path.join(path, *modPath[i:]) + '.es'
		else:
			raise NotImplementedError('absolute imports are not supported, yet')

		if not os.path.exists(toImport):
			s1 = 'can not find module'
			s2 = 'file does not exist: %s' % toImport
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText=s1, postText=s2)

		# now scan the other module for definitions and add them to our namespace
		f = file(toImport, 'rt')
		toImportData = f.read()
		f.close()

		# FIXME FIXME FIXME very ugly hack...
		# use another ModuleTranslator or something like that, then get all definitions and insert them here
		# especially since this process is recursive!
		# this will definitely break when we introduce name mangling!
		import frontend

		numErrors, ast = frontend.sourcecode2AST(toImportData)
		assert(numErrors == 0)

		# extract function declarations from AST
		assert(ast.text == 'MODULE')
		for c in ast.children:
			if c.text == 'DEFFUNC':
				self._onDefProtoype(c)
		


	def _onDefProtoype(self, tree):
		# this function also gets called for functions definitions and should then only generate a prototype
		assert(tree.text == 'DEFFUNC')


		ci = _childrenIterator(tree)
		modifiers = ci.next().text
		name = ci.next().text
		returnType = ci.next().text
		argList = ci.next()

		if returnType == 'int32':
			returnType = Type.int(32)
		elif returnType == 'void':
			returnType = Type.void()
		else:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(1), inlineText='unknown type')


		functionParam_ty = []
		functionParamNames = []
		for i in range(argList.getChildCount() / 2):
			argName = argList.getChild(i * 2).text
			argTypeName = argList.getChild(i * 2 + 1).text

			if argTypeName == 'int32':
				arg_ty = Type.int(32)
			else:
				raise NotImplementedError('unsupported type: %s' % typeName)

			functionParam_ty.append(arg_ty)
			functionParamNames.append(argName)


		funcProto = Type.function(returnType, functionParam_ty)

		# was there already a function with this name?
		# if everything matches, just ignore - otherwise fail
		oldFunc = self._scopeStack.find(name)
		if oldFunc:
			# compare types
			if oldFunc.type.pointee != funcProto:
				s = 'expected type: %s' % oldFunc.type.pointee
				self._raiseException(RecoverableCompileError, tree=tree, inlineText='prototype does not match earlier declaration / definition', postText=s)

			# TODO compare more?
			# maybe add argument names if they were omitted previously?
		else:
			func = self._module.add_function(funcProto, name)

			for i,x in enumerate(functionParamNames):
				func.args[i].name = x

			# add function name to scope
			self._scopeStack.add(name, func)


	def _onDefFunction(self, tree):
		assert(tree.text == 'DEFFUNC')

		ci = _childrenIterator(tree)
		modifiers = ci.next().text
		name = ci.next().text
		returnType = ci.next().text
		argList = ci.next()

		self._onDefProtoype(tree)
		func = self._scopeStack.find(name)
		func.name = name

		# differentiate between declarations and definitions
		if tree.getChildCount() == 4:
			# declaration
			return
		assert(tree.getChild(4).text == 'BLOCK')

		with _ScopeStackWithProxy(self._scopeStack):

			self._currentFunction = func
			entryBB = func.append_basic_block('entry')

			# add variables
			for i in range(len(func.args)):
				self._createAllocaForVar(func.args[i].name, func.args[i].type, func.args[i], treeForErrorReporting=tree)


			addedBRToEntryBB = False
			for x in ci:
				currentBB = func.append_basic_block('bb')
				self._currentBuilder = Builder.new(currentBB)

				if not addedBRToEntryBB:
					b = Builder.new(entryBB)
					b.branch(currentBB)
					addedBRToEntryBB = True

				self._onBlock(x)

			if returnType == 'void':
				self._currentBuilder.ret_void()
			else:
				currentBB = self._currentBuilder.block
				if not (currentBB.instructions and currentBB.instructions[-1].is_terminator):
					# FIXME assert with a good description would be way better...
					lastChild = tree.getChild(tree.getChildCount() - 1)
					s = self._generateContext(preText='warning:', postText='control flow possibly reaches end of non-void function. Inserting trap instruction...', lineBase1=lastChild.line, numAfter=3)
					print s
					trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
					self._currentBuilder.call(trapFunc, [])
					self._currentBuilder.ret(Constant.int(Type.int(32), -1)) # and return, otherwise func.verify will fail
					
				

			func.verify()


	def _onBlock(self, tree):
		assert(tree.text == 'BLOCK')

		with _ScopeStackWithProxy(self._scopeStack):
			for x in _childrenIterator(tree):
				self._dispatch(x)



	def _onReturn(self, tree):
		assert(tree.text == 'return')

		value = self._dispatch(tree.getChild(0))

		expectedRetType = self._currentFunction.type.pointee.return_type
		if value.type != expectedRetType:
			s = 'expected return type: %s' % expectedRetType
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='wrong return type', postText=s)

		self._currentBuilder.ret(value)

	def _onAssert(self, tree):
		assert(tree.text == 'assert')

		# TODO add a compiler switch to disable asserts, so they become noop's
		# TODO add a compiler switch to disable inclusion of context data

		value = self._dispatch(tree.getChild(0))
		value = self._currentBuilder.icmp(IPRED_EQ, value, Constant.int(value.type, 0))

		# if value is statically available bail out now / warn
		# this does not work... investigate later
		#if value == Constant.int(Type.int(1), 0):
		#	print 'assert is always False in %s:%d' % ('???', tree.getLine())

		# now implement an if

		thenBB = self._currentFunction.append_basic_block('assert_true') # trap path
		elseBB = self._currentFunction.append_basic_block('assert_false') # BasicBlock(None) # TODO check if this is really ok

		self._currentBuilder.cbranch(value, thenBB, elseBB)


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
		
		# FIXME the bindings do not currently allow to create BasicBlock's that are not associated to any function
		# so we always append to the end of the function
		# in the generated code this will create a huge mess, but optimization should easily fix this
	
		mergeBB = self._currentFunction.append_basic_block('if_merge')
		# iterate over all 'if' and 'else if' blocks
		for i in range(tree.getChildCount() // 2):
			cond = self._dispatch(tree.getChild(2 * i))
			if cond.type != Type.int(1):
				cond = self._currentBuilder.icmp(IPRED_NE, cond, Constant.int(cond.type, 0))
			
	
			thenBB = self._currentFunction.append_basic_block('if_then')
			elseBB = self._currentFunction.append_basic_block('if_else')

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

		with _ScopeStackWithProxy(self._scopeStack):
			inductVar = self._scopeStack.find(loopVarName)
			if inductVar:
				assert(inductVar.type.pointee == Type.int(32)) # 'range' expects some kind of integer...
			else:
				inductVar = self._createAllocaForVar(loopVarName, Type.int(32))
			start = Constant.int(inductVar.type.pointee, 0)
			step = Constant.int(inductVar.type.pointee, 1)

			if n == 1:
				stop = self._dispatch(loopExpression.getChild(0))
			elif n == 2:
				start = self._dispatch(loopExpression.getChild(0))
				stop = self._dispatch(loopExpression.getChild(1))
			elif n == 3:
				start = self._dispatch(loopExpression.getChild(0))
				stop = self._dispatch(loopExpression.getChild(1))
				step = self._dispatch(loopExpression.getChild(2))

			# setup loop by initializing induction variable
			self._currentBuilder.store(start, inductVar)

			# create blocks
			headBB = self._currentFunction.append_basic_block('head') # decide between Up and Down
			headDownBB = self._currentFunction.append_basic_block('headDown')
			headUpBB = self._currentFunction.append_basic_block('headUp')
			bodyBB = self._currentFunction.append_basic_block('body')
			stepBB = self._currentFunction.append_basic_block('step')
			# TODO: think about implementing an 'else' block, that gets called when the loop does not get executed
			mergeBB = self._currentFunction.append_basic_block('merge')

			self._currentBuilder.branch(headBB)

			# count up or down?
			b = Builder.new(headBB)
			cond = b.icmp(IPRED_SGT, step, Constant.int(step.type, 0))
			b.cbranch(cond, headUpBB, headDownBB)

			# count down check
			b = Builder.new(headDownBB)
			cond = b.icmp(IPRED_SGT, b.load(inductVar), stop)
			b.cbranch(cond, bodyBB, mergeBB)

			# count up check
			b = Builder.new(headUpBB)
			cond = b.icmp(IPRED_SLT, b.load(inductVar), stop)
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
			r = b.add(b.load(inductVar), step)
			b.store(r, inductVar)
			b.branch(headBB)

			# done! continue outside loop body
			self._currentBuilder = Builder.new(mergeBB)


	def _onWhile(self, tree):
		assert(tree.text == 'while')


		with _ScopeStackWithProxy(self._scopeStack):
			# create blocks
			headBB = self._currentFunction.append_basic_block('head')
			bodyBB = self._currentFunction.append_basic_block('body')
			# TODO think about an else block which gets executed iff the body is not executed at least once
			mergeBB = self._currentFunction.append_basic_block('merge')

			# branch to headBB / enter loop
			self._currentBuilder.branch(headBB)

			# create test
			self._currentBuilder = Builder.new(headBB)
			loopExpr = self._dispatch(tree.getChild(0))
			if loopExpr.type != Type.int(1):
				loopExpr = self._currentBuilder.icmp(IPRED_NE, loopExpr, 0)

			self._currentBuilder.cbranch(loopExpr, bodyBB, mergeBB)

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
		

	def _onPass(self, tree):
		assert(tree.text == 'pass')
		# nothing to do here

	def _onIntegerConstant(self, tree):
		assert(tree.text == 'INTEGER_CONSTANT')

		value = tree.getChild(0).text.replace('_', '').lower()

		if value.startswith('0x'):
			i = int(value[2:], 16)
		elif value.startswith('0b'):
			i = int(value[2:], 2)
		elif value.startswith('0') and len(value) > 1:
			i = int(value[1:], 8)
		else:
			i = int(value)
		

		constType = Type.int(32)

		return Constant.int(constType, i)


	def _onFloatConstant(self, tree):
		assert(tree.text == 'FLOAT_CONSTANT')

		value = tree.getChild(0).text.replace('_', '').lower()
		
		f = float(value)

		constType = Type.float()

		return Constant.real(constType, f) # FIXME use float


	def _onVariable(self, tree):
		assert(tree.text == 'VARIABLE')

		varName = tree.getChild(0).text
		ref = self._scopeStack.find(varName)
		if not ref:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='undefined variable name')

		return self._currentBuilder.load(ref)


	def _createAllocaForVar(self, name, type, value=None, treeForErrorReporting=None):
		assert(not isinstance(type, str))

		if type == Type.int(32):
			defaultValue = Constant.int(type, 0)
		else:
			assert(0 and 'unsupported variable type: %s' % type)

		if value == None:
			value = defaultValue

		# check if this variable is already defined
		if self._scopeStack.find(name):
			self._raiseException(RecoverableCompileError, tree=treeForErrorReporting, inlineText='variable already defined: %s' % name)

		# use the usual LLVM pattern to create mutable variables: use alloca
		# important: the mem2reg pass is limited to analyzing the entry block of functions,
		# so all variables must be defined there

		entryBB = self._currentFunction.get_entry_basic_block()
		entryBuilder = Builder.new(entryBB)
		# FIXME workaround: llvm-py segfaults when we call position_at_beginning on an empty block
		if entryBB.instructions:
			entryBuilder.position_at_beginning(entryBB)
		var = entryBuilder.alloca(type, name)
		entryBuilder.store(value, var)

		self._scopeStack.add(name, var)

		return var


	def _onDefVariable(self, tree):
		assert(tree.text == 'DEFVAR')

		varName = tree.getChild(0).text
		varType = tree.getChild(1).text

		if varType == 'int32':
			varType = Type.int(32)
		else:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(1), inlineText='unknown type')

		self._createAllocaForVar(varName, varType, treeForErrorReporting=tree.getChild(0))


	def _onCallFunc(self, tree):
		assert(tree.text == 'CALLFUNC')

		ci = _childrenIterator(tree)
		callee = ci.next().text

		try:
			function = self._module.get_function_named(callee)
		except LLVMException:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='undefined function')


		params = []
		for x in ci:
			r = self._dispatch(x)
			params.append(r)

		# check arguments
		if len(params) != len(function.args):
			s = 'function type: %s' % function.type.pointee
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='wrong number of arguments', postText=s)

		for i in range(len(function.args)):
			if function.args[i].type != params[i].type:
				s = 'argument %d type: %s' % (i + 1, function.args[i].type)
				s2 = 'wrong argument type: %s' % params[i].type
				self._raiseException(RecoverableCompileError, tree=tree.getChild(i + 1), inlineText=s2, postText=s)

		return self._currentBuilder.call(function, params, 'ret_%s' % callee)

	def _onBasicOperator(self, tree):
		nodeType = tree.text
		if tree.getChildCount() == 2 and nodeType in '''* ** // % / and xor or + - < <= == != >= >'''.split():
			first = tree.getChild(0)
			second = tree.getChild(1)

			v1 = self._dispatch(first)
			v2 = self._dispatch(second)

			if nodeType == '*':
				return self._currentBuilder.mul(v1, v2)
			elif nodeType == '**':
				# FIXME we are using the floating point power instead of an integer calculation
				powiFunc = Function.intrinsic(self._module, INTR_POWI, [Type.double()])

				# convert first argument to double
				v1 = self._currentBuilder.sitofp(v1, Type.double())
				
				r = self._currentBuilder.call(powiFunc, [v1, v2])
				return self._currentBuilder.fptosi(r, Type.int(32))
			elif nodeType == '//':# integer division
				return self._currentBuilder.sdiv(v1, v2)
			elif nodeType == '/':# floating point division
				return self._currentBuilder.sdiv(v1, v2) # FIXME use FP div if result is not an integer
			elif nodeType == '%':
				return self._currentBuilder.srem(v1, v2)
			elif nodeType == '+':
				return self._currentBuilder.add(v1, v2)
			elif nodeType == '-':
				return self._currentBuilder.sub(v1, v2)
			elif nodeType in 'and xor or'.split():
				# TODO implement short circuiting!

				# first convert parameters to booleans
				if v1.type != Type.int(1):
					v1 = self._currentBuilder.icmp(IPRED_NE, v1, Constant.int(v1.type, 0))
				if v2.type != Type.int(1):
					v2 = self._currentBuilder.icmp(IPRED_NE, v2, Constant.int(v2.type, 0))
				
				# do check
				if nodeType == 'and':
					r = self._currentBuilder.and_(v1, v2)
				elif nodeType == 'xor':
					r = self._currentBuilder.xor(v1, v2)
				elif nodeType == 'or':
					r = self._currentBuilder.or_(v1, v2)
				else:
					assert(0 and 'dead code path')

				# and go back to int32
				return self._currentBuilder.zext(r, Type.int(32))
			elif nodeType in '< <= == != >= >'.split():
				m = {}
				m['<'] = IPRED_SLT
				m['<='] = IPRED_SLE
				m['=='] = IPRED_EQ
				m['!='] = IPRED_NE
				m['>='] = IPRED_SGE
				m['>'] = IPRED_SGT
				pred = m[nodeType]

				return self._currentBuilder.icmp(pred, v1, v2)
			else:
				assert(0 and 'should never get here')
		elif tree.getChildCount() == 1 and nodeType in '''- + not'''.split():
			v1 = self._dispatch(tree.getChild(0))

			if nodeType == '+':
				return v1
			elif nodeType == '-':
				type_ = Type.int(32)
				return self._currentBuilder.sub(Constant.int(type_, 0), v1)
			elif nodeType == 'not':
				r = self._currentBuilder.icmp(IPRED_EQ, v1, Constant.int(v1.type, 0))

				return self._currentBuilder.zext(r, Type.int(32))
			else:
				assert(0 and 'dead code path')
		else:
			raise NotImplementedError('basic operator \'%s\' not yet implemented' % nodeType)

	def _simpleAssignment(self, name, value, treeForErrorReporting=None):
		ref = self._scopeStack.find(name)
		if ref:
			# variable already exists

			# check type
			if value.type != ref.type.pointee:
				s1 = 'expression is of incompatible type'
				s2 = 'lhs type: %s; rhs type: %s' % (ref.type.pointee, value.type)
				self._raiseException(RecoverableCompileError, tree=treeForErrorReporting, inlineText=s1, postText=s2)
			self._currentBuilder.store(value, ref)
		else:
			# new variable
			# do not pass value when creating the variable! The value is NOT available in the entry block (at least in general)!
			self._createAllocaForVar(name, value.type, treeForErrorReporting=treeForErrorReporting)

			ref = self._scopeStack.find(name)
			self._currentBuilder.store(value, ref)
		
		return ref

	def _onAssign(self, tree):
		assert(tree.text == '=')

		n = tree.getChildCount()
		names = []
		for i in range(n - 1):
			names.append(tree.getChild(i).text)

		value = self._dispatch(tree.getChild(n - 1))

		# transform assignments in the form
		#     a = b = c = expr;
		# to
		#     c = expr; b = c; a = b;
		# instead of
		#     c = expr; b = expr; a = expr;
		# this form avoids any problems related to already existing variables with different types

		lastResult = value;
		for i, name in enumerate(names):
			ref = self._simpleAssignment(name, lastResult, treeForErrorReporting=tree.getChild(i + 1))

			if ref.type != lastResult.type:# when we get different types this gets finally called and must do some conversions
				lastResult = self._currentBuilder.load(ref)


		return lastResult # TODO really needed?

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
			ref = self._currentBuilder.alloca(value.type, 'listassign_tmp')
			self._currentBuilder.store(value, ref)
			temps.append(ref)

		# copy temp -> destination
		# this is a simple assignment
		for i in range(n):
			value = self._currentBuilder.load(temps[i])
			destination = lhs.getChild(i).text

			self._simpleAssignment(destination, value)




	def _dispatch(self, tree):
		return self._dispatchTable[tree.text](tree)



	def translateAST(self, tree, absFilename, sourcecode=''):
		assert(tree.text == 'MODULE')

		assert(os.path.isabs(absFilename))

		self._filename = absFilename
		self._sourcecode = sourcecode
		self._sourcecodeLines = sourcecode.splitlines()

		self._module = None


		self._dispatch(tree)

		self._module.verify()

		return self._module

	

def run(module, function):
	mp = ModuleProvider.new(module)
	ee = ExecutionEngine.new(mp)

	return ee.run_function(function, [])



