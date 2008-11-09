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
from scopestack import ScopeStack, ScopeStackWithProxy
from typesystem import *
from esfunction import ESFunction
from esvalue import ESValue
from esvariable import ESVariable

def _childrenIterator(tree):
	n = tree.getChildCount()
	for i in range(n):
		yield tree.getChild(i)




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
		self._dispatchTable['MODULESTART'] = self._onModuleStart
		self._dispatchTable['package'] = self._onPackage
		self._dispatchTable['module'] = self._onModule
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
		


	def _addHelperFunctionsPreTranslation(self):
		# puts
		retType= Type.int(32)
		parameterTypes = []
		parameterTypes.append(Type.pointer(Type.int(8)))
		functionType = Type.function(retType, parameterTypes)
		func = self._module.add_function(functionType, 'puts')
		self._scopeStack.add('puts', func)

		# abort
		functionType = Type.function(Type.void(), [])
		func = self._module.add_function(functionType, 'abort')
		self._scopeStack.add('abort', func)


	def _addHelperFunctionsPostTranslation(self):
		# if this module contains a main function emit code which will call it

		flist = self._scopeStack.find('main')

		if flist:# other checks prevent flist being longer than 1 element
			# generate code too call main
			mainFunc = flist[0]

			s = []
			s.append('The main function defined in this module has an unsupported signature.')
			s.append('supported signatures:')
			s.append('\tdef main() as int32')
			s.append('\tdef main() as void')


			# incompatible return type?
			retType = mainFunc.type.pointee.return_type
			if retType != Type.void() and retType != Type.int(32):
				self._raiseException(RecoverableCompileError, postText=s)

			# has arguments?
			if len(mainFunc.args) == 0:
				functionType= Type.function(Type.int(32), [])
				function = self._module.add_function(functionType, 'main')

				entryBB = function.append_basic_block('entry')
				BB = function.append_basic_block('bb')

				b = Builder.new(entryBB)
				b.branch(BB)

				b = Builder.new(BB)
				r = b.call(mainFunc, [])

				if retType != Type.void():
					b.ret(r)
				else:
					b.ret(Constant.int(Type.int(32), 0))
			else:
				# TODO implement version with parameters
				self._raiseException(RecoverableCompileError, postText=s)






	def _onModuleStart(self, tree):
		assert(tree.text == 'MODULESTART')

		self._errors = 0
		self._warnings = 0

		self._module = Module.new('main_module')
		self._scopeStack = ScopeStack() # used to resolve variables
		self._breakTargets = [] # every loop pushes / pops basic blocks onto this stack for usage by break.
		self._continueTargets = [] # see breakTargets

		self._moduleName = os.path.split(self._filename)[1] 
		self._packageName = ''

		# first pass: process package and module statements
		# if these statements exist they are the first two
		for x in tree.children[:2]:
			if x.text in ['package', 'module']:
				self._dispatch(x)

		# make sure package and module names are valid
		m = re.match('[a-zA-Z_][a-zA-Z_0-9]*', self._moduleName)
		bad = True
		if m and m.span() == (0, len(self._moduleName)):
			bad = False
		if bad:
			self._raiseException(CompileError, postText='Module filenames should begin with alpha character or underscore otherwise it\'s not possible to import them. To disable this error message set a valid module name using the \'module\' statement.')

		# add some helper functions / prototypes / ... to the module
		self._addHelperFunctionsPreTranslation()

		# second pass: make all functions available, so we don't need any stupid forward declarations
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


		# third pass: translate code
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

		# finally add some more helper functions / prototypes / ... to the module
		self._addHelperFunctionsPostTranslation()


	def _onPackage(self, tree):
		assert(tree.text == 'package')

		self._packageName = tree.children[0].text

	def _onModule(self, tree):
		assert(tree.text == 'module')

		self._moduleName = tree.children[0].text


	def _onImportAll(self, tree):
		assert(tree.text == 'IMPORTALL')
		assert(os.path.isabs(self._filename)) # also checked in translateAST, but be really sure


		# get path to other module
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

		# load data
		f = file(toImport, 'rt')
		toImportData = f.read()
		f.close()


		# tricky part:
		#     translate module to AST
		#     use *another* module translator to translate the module
		#         recurse, if necessary
		#     export symbols
		#     insert symbols in our module

		# FIXME possible infinite recursion: circular dependencies are not detected
		# FIXME very inefficient:
		#     ideally first a dependency graph is generated
		#     this can be used by any make like tool to instruct the compiler to generate (precompiled???) headers
		#     the headers can be parsed much faster
		#     additionally we should maintain an internal list of already parsed modules
		import frontend

		numErrors, ast = frontend.sourcecode2AST(toImportData)
		if numErrors:
			self._raiseException(CompileError, tree=tree.children[0], inlineText='module contains errors')

		mt = ModuleTranslator()
		mt.translateAST(ast, toImport, toImportData)
		d = mt._exportGloballyVisibleSymbols()


		# many strange things can happen here
		# assume a user has two modules with the same package names, same module names
		# and then defines in both modules a function
		#     def f() as int32;
		# but with different bodies. Now both function get the same mangled name and we have no idea which one to use...
		# At least this case will generate a linker error
		for x in d['functions']:
			try:
				self._module.get_function_named(x['mangledName'])
				mangledName = True
			except:
				mangledName = False

			if not mangledName:
				func = self._module.add_function(x['type'], x['mangledName'])
				self._scopeStack.add(x['name'], func)
			else:
				# check that types match
				blockers = self._scopeStack.find(x['name']) # FIXME is this really enough? maybe we should scan all functions to get the offending one
				match = False
				for b in blockers:
					if b.type.pointee == x['type']:
						match = True

				if not match:
					# that's bad! That means self._scopeStack.find(x['name']) is not enough to find all offenders!
					# maybe another bug, too...
					s1 = 'module caused internal error'
					s2 = ['imported module contains a function with the same mangled name as a function in the current module']
					s2.append('name: %s; mangled name: %s' % (x['name'], x['mangledName']))
					s2.append('Internal compiler error. Please submit a bug report.')
					s2 = '\n'.join(s2)
					self._raiseException(CompileError, tree=tree.children[0], inlineText=s1, postText=s2)


		# TODO import other symbols, types, etc




	def _onDefProtoype(self, tree):
		# this function also gets called for functions definitions and should then only generate a prototype
		assert(tree.text == 'DEFFUNC')


		ci = _childrenIterator(tree)
		modifiers = ci.next()
		name = ci.next().text
		returnTypeName = ci.next().text
		argList = ci.next()

		if returnTypeName == 'int32':
			returnType = Type.int(32)
		elif returnTypeName == 'void':
			returnType = Type.void()
		else:
			self._raiseException(RecoverableCompileError, tree=tree.getChild(1), inlineText='unknown type')


		functionParam_ty = []
		functionParamTypeNames = []
		functionParamNames = []
		for i in range(argList.getChildCount() / 2):
			argName = argList.getChild(i * 2).text
			argTypeName = argList.getChild(i * 2 + 1).text

			if argTypeName == 'int32':
				arg_ty = Type.int(32)
			else:
				raise NotImplementedError('unsupported type: %s' % typeName)

			functionParam_ty.append(arg_ty)
			functionParamTypeNames.append(argTypeName)
			functionParamNames.append(argName)


		funcProto = Type.function(returnType, functionParam_ty)

		# parse modifiers
		modMangling = 'default'
		for i in range(modifiers.getChildCount() / 2):
			key = modifiers.children[2 * i].text
			value = modifiers.children[2 * i + 1].text

			# TODO implement better checking, duplicate keys etc.

			if key == 'mangling':
				if value not in ['C', 'default']:
					self._raiseException(RecoverableCompileError, tree=tree.children[2 * i + 1], inlineText='unknown function modifier')
				modMangling = value
			else:
				self._raiseException(RecoverableCompileError, tree=tree.children[2 * i], inlineText='unknown function modifier')


		# was there already a function with this name?
		# check according to overload rules if everything is ok with this declaration
		functionsWithThisName = self._scopeStack.find(name)

		func = None
		if functionsWithThisName:
			for other in functionsWithThisName:
				# TODO think about limitations of overloading

				# check that a function is not defined several times using the same (returnType, paramterTypes)
				if other.type.pointee == funcProto:
					func = other
					break

		if not func:
			if name == 'main':# a user defined main gets called by a compiler defined main function
				mangledName = '__ES_main'
			elif modMangling == 'C':
				mangledName = name
			else:
				mangledName = mangleFunction(self._packageName, self._moduleName, name, returnTypeName, functionParamTypeNames)

			# a function with a matching signature was not found
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


			func = self._module.add_function(funcProto, mangledName)
			
			for i,x in enumerate(functionParamNames):
				func.args[i].name = x

			# add function name to scope
			self._scopeStack.add(name, func)

		return func

		# add function
		#if oldFunc:
		#	# compare types
		#	if oldFunc.type.pointee != funcProto:
		#		s = 'expected type: %s' % oldFunc.type.pointee
		#		self._raiseException(RecoverableCompileError, tree=tree, inlineText='prototype does not match earlier declaration / definition', postText=s)

		#	# TODO compare more?
		#	# maybe add argument names if they were omitted previously?
		#else:

	

	def _onDefFunction(self, tree):
		assert(tree.text == 'DEFFUNC')

		ci = _childrenIterator(tree)
		modifiers = ci.next().text
		name = ci.next().text
		returnType = ci.next().text
		argList = ci.next()

		func = self._onDefProtoype(tree)

		# differentiate between declarations and definitions
		if tree.getChildCount() == 4:
			# declaration
			return
		assert(tree.getChild(4).text == 'BLOCK')

		with ScopeStackWithProxy(self._scopeStack):

			self._currentFunction = func
			entryBB = func.append_basic_block('entry')

			# add variables
			for i in range(len(func.args)):
				self._createAllocaForVar(func.args[i].name, func.args[i].type, u'int32', func.args[i], treeForErrorReporting=tree) # FIXME use real argument type


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
					lastChild = tree.getChild(tree.getChildCount() - 1)
					s = self._generateContext(preText='warning:', postText='control flow possibly reaches end of non-void function. Inserting trap instruction...', lineBase1=lastChild.line, numAfter=3)
					print s
					trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
					self._currentBuilder.call(trapFunc, [])
					self._currentBuilder.ret(Constant.int(Type.int(32), -1)) # and return, otherwise func.verify will fail
					
				

			func.verify()


	def _onBlock(self, tree):
		assert(tree.text == 'BLOCK')

		with ScopeStackWithProxy(self._scopeStack):
			for x in _childrenIterator(tree):
				self._dispatch(x)



	def _onReturn(self, tree):
		assert(tree.text == 'return')

		esValue = self._dispatch(tree.getChild(0))

		expectedRetType = self._currentFunction.type.pointee.return_type
		if esValue.llvmType != expectedRetType:
			esValue = self._convertType(esValue, u'int32') # FIXME use real type, not hard coded one
			#s = 'expected return type: %s' % expectedRetType
			#self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='wrong return type', postText=s)

		self._currentBuilder.ret(esValue.llvmValue)

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

		thenBB = self._currentFunction.append_basic_block('assert_true') # trap path
		elseBB = self._currentFunction.append_basic_block('assert_false') # BasicBlock(None) # TODO check if this is really ok

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
		
		mergeBB = self._currentFunction.append_basic_block('if_merge')
		# iterate over all 'if' and 'else if' blocks
		for i in range(tree.getChildCount() // 2):
			condESValue = self._dispatch(tree.getChild(2 * i))
			if condESValue.llvmType != Type.int(1):# FIXME use comparison against bool?
				cond = self._currentBuilder.icmp(IPRED_NE, condESValue.llvmValue, Constant.int(condESValue.llvmType, 0)) # FIXME use conversion to bool
			else:
				cond = condESValue.llvmValue

			
	
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
			headBB = self._currentFunction.append_basic_block('head')
			bodyBB = self._currentFunction.append_basic_block('body')
			# TODO think about an else block which gets executed iff the body is not executed at least once
			mergeBB = self._currentFunction.append_basic_block('merge')

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

		# TODO move this into ESIntegerType?
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
			self._raiseException(RecoverableCompileError, tree=tree.children[0], inlineText='constant can not be represented by an int64')

		# FIXME TODO think about a default type. int8 is somewhat inconvenient as a default type...
		# for now just use int32 that works on every x86 / x86_84 etc.
		if bits < 32:
			bits = 32
		
		c = Constant.int(Type.int(bits), i)
		v = ESValue(c, u'int%d' % bits)

		return v


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

		entryBB = self._currentFunction.get_entry_basic_block()
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
		# FIXME
		function = None
		for f in functions:
			if len(f.args) == nArguments:
				function = f
				break

		if not function:
			s1 = 'no matching function found'
			s2 = ['canditates:']
			for f in functions:
				s2.append('\t%s' % f.type.pointee)
			s2 = '\n'.join(s2)
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText=s1, postText=s2)


		params = []
		for x in ci:
			r = self._dispatch(x)
			params.append(r)

		# check arguments
		# TODO check against ES types!
		if len(params) != len(function.args):
			s = 'function type: %s' % function.type.pointee
			self._raiseException(RecoverableCompileError, tree=tree.getChild(0), inlineText='wrong number of arguments', postText=s)

		for i in range(len(function.args)):
			if function.args[i].type != params[i].llvmType:
				# try implicit conversion
				try:
					params[i] = self._convertType(params[i], u'int32') # FIXME use real type
				except CompileError, NotImplementedError:
					s = 'argument %d type: %s' % (i + 1, function.args[i].type)
					s2 = 'wrong argument type: %s' % params[i].type
					self._raiseException(RecoverableCompileError, tree=tree.getChild(i + 1), inlineText=s2, postText=s)

		r = self._currentBuilder.call(function, [x.llvmValue for x in params], 'ret_%s' % callee)
		return ESValue(r, u'int32') # FIXME

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
			ref = self._currentBuilder.alloca(value.llvmType, 'listassign_tmp')
			self._currentBuilder.store(value.llvmValue, ref)
			temps.append(ESVariable(ref, value.typename, 'listassign_tmp'))

		# copy temp -> destination
		# this is a simple assignment
		for i in range(n):
			value = self._currentBuilder.load(temps[i].llvmRef)
			destination = lhs.getChild(i).text

			self._simpleAssignment(destination, ESValue(value, temps[i].typename))




	def _dispatch(self, tree):
		return self._dispatchTable[tree.text](tree)



	def translateAST(self, tree, absFilename, sourcecode=''):
		assert(tree.text == 'MODULESTART')

		assert(os.path.isabs(absFilename))

		self._filename = absFilename
		self._sourcecode = sourcecode
		self._sourcecodeLines = sourcecode.splitlines()

		self._module = None


		self._dispatch(tree)

		self._module.verify()


		return self._module


	def _exportGloballyVisibleSymbols(self):
		assert(self._module and 'run translateAST first')

		# globally visible symbols
		d = {}
		d['package'] = self._packageName
		d['module'] = self._moduleName

		functions = []
		d['functions'] = functions

		for key, value in self._scopeStack._stack[0].items():
			if type(value) == list:
				# function
				for x in value:
					f = {}
					f['name'] = key
					f['mangledName'] = x.name
					f['type'] = x.type.pointee

					functions.append(f)
			else:
				# global variable
				assert(0 and 'no global variables supported')

		return d

	def _convertType(self, esValue, toType, warn=True):
		# TODO refactor code into external functions
		assert(isinstance(esValue, ESValue))
		assert(isinstance(toType, unicode))

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
			raise NotImplementedError()

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
			raise NotImplementedError


	

def run(module, function):
	mp = ModuleProvider.new(module)
	ee = ExecutionEngine.new(mp)

	return ee.run_function(function, [])



