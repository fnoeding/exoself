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

import setuppaths
from errors import CompileError, RecoverableCompileError
import os
import astwalker
from estype import ESType
from esfunction import ESFunction
from esvariable import ESVariable
import estypesystem
from symboltable import SymbolTable
from tree import Tree, TreeType
import re


class ASTTypeAnnotator(astwalker.ASTWalker):
	def walkAST(self, ast, filename, sourcecode=''):
		astwalker.ASTWalker.walkAST(self, ast, filename, sourcecode)



	def _initModuleSymbolTable(self):
		self._moduleNode.symbolTable = SymbolTable()
		st = self._moduleNode.symbolTable

		for k, v in estypesystem.elementaryTypes.items():
			st.addSymbol(k, v)

	
	def _insertCastNode(self, exprNode, toTypeName):
		newExprNode = exprNode.copy(True)
		typeNameNode = exprNode.copy(False)

		typeNameNode.type = TreeType.NAME # FIXME this should be later a typename node
		typeNameNode.text = toTypeName

		exprNode.type = TreeType.CAST
		exprNode.text = u'CAST'
		exprNode.children = [typeNameNode, newExprNode]
		exprNode.esType = self._findSymbol(name=toTypeName, type_=ESType)


	def _onModuleStart(self, ast, packageName, moduleName, statements):
		self._moduleNode = ast
		self._symbolTables = []
		ast.symbolTable = None

		if packageName:
			ast.packageName = packageName.text
		else:
			ast.packageName = ''

		if moduleName:
			ast.moduleName = moduleName.text
		else:
			ast.moduleName = None

		if not ast.moduleName:
			# use filename
			# TODO error / warn if filename is not a suitable module name
			ast.moduleName = os.path.split(self._filename)[1]

		# make sure module name is valid
		m = re.match('[a-zA-Z_][a-zA-Z_0-9]*', ast.moduleName)
		bad = True
		if m and m.span() == (0, len(ast.moduleName)):
			bad = False
		if bad:
			self._raiseException(CompileError, postText='Module filenames should begin with alpha character or underscore otherwise it\'s not possible to import them. To disable this error message set a valid module name using the \'module\' statement.')


		############################################
		# init some important data structures
		############################################
		self._initModuleSymbolTable()
		self._symbolTables = [ast.symbolTable]


		############################################
		# import stuff
		############################################
		for x in statements:
			if x.type in [TreeType.IMPORTALL]:
				self._dispatch(x)

		############################################
		# get global variables and functions
		############################################
		old = self._onDefFunction
		self._onDefFunction = self._onFuncPrototype
		for x in statements:
			if x.type == TreeType.DEFFUNC:
				self._dispatch(x) # do not directly call _onFuncPrototype; _dispatch manages _nodes field
		self._onDefFunction = old

		############################################
		# annotate the whole tree
		############################################
		for x in statements:
			if x.type in [TreeType.IMPORTALL]:
				# already done
				continue

			self._dispatch(x)

	def _onImportAll(self, ast, moduleName):
		assert(os.path.isabs(self._filename))

		# get path to other module
		modPath = moduleName.text	
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
			self._raiseException(RecoverableCompileError, tree=moduleName, inlineText=s1, postText=s2)

		# load data
		f = file(toImport, 'rt')
		toImportData = f.read()
		f.close()


		# tricky part:
		#     translate module to AST
		#     use *another* type annotator to translate the module
		#         recurse, if necessary
		#     export symbols
		#     insert symbols in our module

		# FIXME possible infinite recursion: circular dependencies are not detected
		# FIXME very inefficient:
		#     ideally first a dependency graph is generated
		#     this can be used by any make like tool to instruct the compiler to generate (precompiled???) headers
		#     the headers can be parsed much faster
		#     additionally we should maintain an internal list of already parsed modules
		from source2ast import sourcecode2AST

		numErrors, ast = sourcecode2AST(toImportData)
		if numErrors:
			self._raiseException(CompileError, tree=moduleName, inlineText='module contains errors')

		mt = ASTTypeAnnotator()
		mt.walkAST(ast, toImport, toImportData)


		# many strange things can happen here
		# assume a user has two modules with the same package names, same module names
		# and then defines in both modules a function
		#     def f() as int32;
		# but with different bodies. Now both function get the same mangled name and we have no idea which one to use...
		# At least this case will generate a linker error

		# get global symbols
		st = mt._moduleNode.symbolTable
		symbols = st.getAllSymbols()

		for k, v in symbols.items():
			# FIXME for now only copy ESFunction's and especially not ESType's to avoid name clashes
			if isinstance(v, list):
				for x in v:
					assert(isinstance(x, ESFunction))
					self._addSymbol(name=k, symbol=x)
					print x




	def _onFuncPrototype(self, ast, modifierKeys, modifierValues, name, returnTypeName, parameterNames, parameterTypeNames, block):
		# create type of function
		returnTypes = [self._findSymbol(fromTree=returnTypeName, type_=ESType)]

		paramNames = []
		paramTypes = []
		for i in range(len(parameterTypeNames)):
			paramNames.append(parameterNames[i].text)
			type_ = self._findSymbol(fromTree=parameterTypeNames[i], type_=ESType)

			paramTypes.append(type_)

		functionType = ESType.createFunction(returnTypes, paramTypes)


		# parse modifiers
		linkage = None
		mangling = None
		for i in range(len(modifierKeys)):
			k = modifierKeys[i].text
			v = modifierValues[i].text

			if k == u'linkage':
				linkage = v
			elif k == u'mangling':
				mangling = v
			else:
				self._raiseException(RecoverableCompileError, tree=modifierKeys[i], inlineText='unknown function modifier')
		

		esFunction = ESFunction(name.text, self._moduleNode.packageName, self._moduleNode.moduleName, functionType, paramNames, mangling=mangling, linkage=linkage)
		ast.esFunction = esFunction

		# TODO check for duplicate entries
		self._addSymbol(fromTree=name, symbol=esFunction)


	def _onDefFunction(self, ast, modifierKeys, modifierValues, name, returnTypeName, parameterNames, parameterTypeNames, block):
		if not block:
			# it's only a prototype --> already all work done by _onFuncPrototype in preprocessing phase
			return

		# add a new symbol table and add entries for parameter names
		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.

		esFunction = ast.esFunction
		esParamTypes = esFunction.esType.getFunctionParameterTypes()
		for i in range(len(esFunction.parameterNames)):
			varName=parameterNames[i].text
			esVar = ESVariable(varName, esParamTypes[i])
			self._addSymbol(fromTree=parameterNames[i], symbol=esVar)

		blockNode = ast.children[4]
		self._dispatch(blockNode)


	def _onBlock(self, ast, blockContent):
		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.	

		for x in blockContent:
			self._dispatch(x)

	
	def _onPass(self, ast):
		pass


	def _onReturn(self, ast, expressions):
		# find enclosing function definion
		esFunction = None
		for n in reversed(self._nodes[:-1]):
			esFunction = getattr(n, 'esFunction', None)
			if esFunction:
				break

		if not esFunction:
			self._raiseException(CompileError, tree=ast, inlineText='a \'return\' statement must be inside a function body')

		returnTypes = esFunction.esType.getFunctionReturnTypes()

		assert(len(returnTypes) <= 1)

		if not returnTypes:
			# function returns 'void'
			if len(expressions) > 0:
				self._raiseException(RecoverableCompileError, tree=ast, inlineText='function is declared as void: can\'t return anything')

		else:
			for i, x in enumerate(expressions):
				self._dispatch(x)
				t = x.esType # every expression must have an esType member

				# FIXME provide implicit conversion support 
				if not t.isEquivalentTo(returnTypes[i], False):
					# types did not match, try implicit cast
					if not estypesystem.canImplicitlyCast(t, returnTypes[i]):
						self._raiseException(RecoverableCompileError, tree=expressions[i], inlineText='incompatible return type')

					self._insertCastNode(expressions[i], u'int32') # FIXME use real type



	def _onIntegerConstant(self, ast, value):
		signed = True # default, if nothing is specified

		if signed:
			if -(2 ** 7) <= value <= 2 ** 7 - 1:
				bits = 8
			elif -(2 ** 15) <= value <= 2 ** 15 - 1:
				bits = 16
			elif -(2 ** 31) <= value <= 2 ** 31 - 1:
				bits = 32
			elif -(2 ** 63) <= value <= 2 ** 63 - 1:
				bits = 64
			else:
				self._raiseException(RecoverableCompileError, tree=ast, inlineText='constant can not be represented by an int64')
		else:
			raise NotImplementedError('uintN not supported, yet')

		# FIXME enforce a default type
		if bits < 32:
			bits = 32

		if signed:
			ast.esType = self._findSymbol(name=u'int%d' % bits, type_=ESType)
		else:
			ast.esType = self._findSymbol(name=u'uint%d' % bits, type_=ESType)


	def _onBasicOperator(self, ast, op, arg1, arg2):
		tt = TreeType

		# arg1 is always valid, arg2 may be None
		self._dispatch(arg1)
		if arg2:
			self._dispatch(arg2)

		# fetch some types
		bool = self._findSymbol(name=u'bool', type_=ESType)
		int32 = self._findSymbol(name=u'int32', type_=ESType)
		single = self._findSymbol(name=u'single', type_=ESType)
		double = self._findSymbol(name=u'double', type_=ESType)


		if op in [tt.AND, tt.XOR, tt.OR]:
			if not arg1.esType.isEquivalentTo(bool, False):
				self._insertCastNode(arg1, u'bool')

			if not arg2.esType.isEquivalentTo(bool, False):
				self._insertCastNode(arg2, u'bool')

			ast.esType = bool
		elif op in [tt.NOT]:
			if not arg1.esType.isEquivalentTo(bool, False):
				self._insertCastNode(arg1, u'bool')

			ast.esType = bool
		elif op in [tt.PLUS, tt.MINUS]:
			if not arg2:
				ast.esType = arg1.esType
				return

			# FIXME for now only int32 is supported
			if not arg1.esType.isEquivalentTo(int32, False):
				self._insertCastNode(arg1, u'int32')

			if not arg2.esType.isEquivalentTo(int32, False):
				self._insertCastNode(arg2, u'int32')

			ast.esType = int32
		elif op in [tt.STAR, tt.SLASH, tt.PERCENT]:
			if arg1.esType.isEquivalentTo(arg2.esType, False):
				ast.esType = arg1.esType
				return

			print arg1.esType, arg2.esType

			raise NotImplementedError('TODO')
		elif op in [tt.DOUBLESTAR]:
			# base: arg1; exponent: arg2
			# powi: arg1 any float, arg2 int32
			# pow: arg1 any float, arg2 same type as arg1

			# FIXME for now only powi
			if not arg2.esType.isEquivalentTo(int32, False):
				self._insertCastNode(arg2, u'int32')

			if not (arg1.esType.isEquivalentTo(single, False) or arg1.esType.isEquivalentTo(double, False)):
				self._insertCastNode(arg1, u'double')
			else:
				raise NotImplementedError('TODO')


			if arg1.esType.isEquivalentTo(single, False):
				ast.esType = single
			elif arg1.esType.isEquivalentTo(double, False):
				ast.esType = double
			else:
				raise NotImplementedError('TODO')
		elif op in [tt.LESS, tt.LESSEQUAL, tt.EQUAL, tt.NOTEQUAL, tt.GREATEREQUAL, tt.GREATER]:
			# FIXME for now only int32 supported
			if not arg1.esType.isEquivalentTo(int32, False):
				self._insertCastNode(arg1, u'int32')

			if not arg2.esType.isEquivalentTo(int32, False):
				self._insertCastNode(arg2, u'int32')

			ast.esType = bool
		else:
			raise NotImplementedError('operator not implemented: %s / %s' % (op, ast.text))


	def _onCallFunc(self, ast, calleeName, expressions):
		for x in expressions:
			self._dispatch(x)

		esFunctions = self._findSymbol(fromTree=calleeName, type_=ESFunction)

		# TODO find best matching function for parameters
		# for now simply match argument count
		callee = None
		for f in esFunctions:
			if len(f.esType.getFunctionParameterTypes()) == len(expressions):
				callee = f
				break

		if not callee:
			self._raiseException(RecoverableCompileError, tree=calleeName, inlineText='no matching function found')


		returnTypes = callee.esType.getFunctionReturnTypes()
		assert(len(returnTypes) == 1)

		ast.esType = returnTypes[0] # TODO implement support for multiple return values
		ast.esFunction = callee


	def _onVariable(self, ast, variableName):
		s = self._findSymbol(fromTree=variableName, type_=ESVariable)

		ast.esType = s.esType

	def _onAssert(self, ast, expression):
		self._dispatch(expression)

		esType = expression.esType
		if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
			if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
				self._raiseException(RecoverableCompileError, tree=expression, inlineText='expression is of incompatible type. expected bool')

			self._insertCastNode(expression, u'bool')


	def _onIf(self, ast, expressions, blocks, elseBlock):
		for x in expressions:
			self._dispatch(x)

		for i in range(len(expressions)):
			esType = expressions[i].esType

			if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
				if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
					self._raiseException(RecoverableCompileError, tree=expressions[i], inlineText='expression is of incompatible type. expected bool')

				self._insertCastNode(expressions[i], u'bool')

		for x in blocks:
			self._dispatch(x)

		if elseBlock:
			self._dispatch(elseBlock)


	def _onDefVariable(self, ast, variableName, typeName):
		esType = self._findSymbol(fromTree=typeName, type_=ESType)
		esVar = ESVariable(variableName.text, esType)
		self._addSymbol(fromTree=variableName, symbol=esVar)


	def _onAssignHelper(self, varNameNode, exprNode):
		self._dispatch(exprNode)
		esType = exprNode.esType

		try:
			var = self._findSymbol(fromTree=varNameNode, type_=ESVariable)
		except CompileError:
			var = None

		if not var:
			# create new variable with type of expression
			var = ESVariable(varNameNode.text, esType)
			self._addSymbol(fromTree=varNameNode, symbol=var)
		else:
			if not var.esType.isEquivalentTo(esType, False):
				if not estypesystem.canImplicitlyCast(esType, var.esType):
					self._raiseException(RecoverableCompileError, tree=exprNode, inlineText='incompatible type')

				# TODO insert CAST node
				raise NotImplementedError('insert cast node here')


	
	def _onAssign(self, ast, variableName, expression):
		self._onAssignHelper(variableName, expression)


	def _onListAssign(self, ast, variableNames, expressions):
		# semantics of list assign in cases where a variable is referenced on both sides:
		# 1st copy results of ALL expressions into temporary variables
		# 2nd copy content of temporary variables to destination variables
		# --> just assign esType of n-th expression to n-th assignee

		for i in range(len(expressions)):
			self._onAssignHelper(variableNames[i], expressions[i])


	def _onFor(self, ast, variableName, rangeStart, rangeStop, rangeStep, block):
		ast.symbolTable = SymbolTable() # do not use directly!

		if rangeStart:
			self._dispatch(rangeStart)
		if rangeStop:
			self._dispatch(rangeStop)
		if rangeStep:
			self._dispatch(rangeStep)

		# TODO emit warnings if range would overflow induct var type

		# FIXME for now only int32 support
		int32 = self._findSymbol(name=u'int32', type_=ESType)
		badNode = None
		if rangeStart and not rangeStart.esType.isEquivalentTo(int32, False):
			bad = rangeStart
		if rangeStop and not rangeStop.esType.isEquivalentTo(int32, False):
			bad = rangeStop
		if rangeStep and not rangeStep.esType.isEquivalentTo(int32, False):
			bad = rangeStep

		if badNode:
			self._raiseException(RecoverableCompileError, tree=badNode, inlineText='range expressions are currently only implemented for int32')

		try:
			var = self._findSymbol(fromTree=variableName, type_=ESVariable)
		except CompileError:
			var = None

		if var:
			if not var.esType.isEquivalentTo(int32, False):
				self._raiseException(RecoverableCompileError, tree=variableName, inlineText='loop variable must be of type int32 until support for other types is implemented')
		else:
			var = ESVariable(variableName.text, int32)
			self._addSymbol(fromTree=variableName, symbol=var)
			
		self._dispatch(block)


	def _onBreak(self, ast):
		ok = False
		for n in reversed(self._nodes):
			if n.type in [TreeType.FOR, TreeType.WHILE]:# TODO add 'case' / 'switch'
				ok = True
				break

		if not ok:
			self._raiseException(RecoverableCompileError, tree=ast, inlineText='may only be used inside for, while, switch and similar constructs')


	def _onContinue(self, ast):
		ok = False
		for n in reversed(self._nodes):
			if n.type in [TreeType.FOR, TreeType.WHILE]:
				ok = True
				break

		if not ok:
			self._raiseException(RecoverableCompileError, tree=ast, inlineText='may only be used inside for, while and similar constructs')


	def _onWhile(self, ast, expression, block):
		self._dispatch(expression)

		esType = expression.esType
		bool = self._findSymbol(name=u'bool', type_=ESType)
		if not esType.isEquivalentTo(bool, False):
			# types did not match, try implicit cast
			if not estypesystem.canImplicitlyCast(esType, bool):
				self._raiseException(RecoverableCompileError, tree=expression, inlineText='incompatible type, expected bool')

			# TODO add cast node


		self._dispatch(block)






