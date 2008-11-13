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


class ASTTypeAnnotator(astwalker.ASTWalker):
	def walkAST(self, ast, filename, sourcecode=''):
		astwalker.ASTWalker.walkAST(self, ast, filename, sourcecode)

		print ast.symbolTable


	def _initModuleSymbolTable(self):
		self._moduleNode.symbolTable = SymbolTable()
		st = self._moduleNode.symbolTable

		for k, v in estypesystem.elementaryTypes.items():
			st.addSymbol(k, v)

	def _findSymbolHelper(self, name):
		# start at current symbol table, then walk all AST nodes containing symbol tables until root node. Stop search when something was found
		results = []
		for ast in reversed(self._nodes):
			st = getattr(ast, 'symbolTable', None)
			if not st:
				continue

			s = st.findSymbol(name)
			if not s:
				continue

			if isinstance(s, list):
				results.extend(s)
			else:
				return s

		if results:
			return results
		else:
			return None


	def _findSymbol(self, **kwargs): # fromTree=None, name=None, type_=None
		if 'name' in kwargs:
			name = kwargs['name']
			fromTree = None
		else:
			fromTree = kwargs['fromTree']
			name = fromTree.text

		type_ = kwargs['type_']


		s = self._findSymbolHelper(name)

		if not s:
			self._raiseException(RecoverableCompileError, tree=fromTree, inlineText='could not find symbol')
		if type_:
			bad = False
			if type_ == ESFunction:
				if not isinstance(s, list):
					bad = True
			elif not isinstance(s, type_):
				bad = True

			if bad:
				self._raiseException(RecoverableCompileError, tree=fromTree, inlineText='symbol did not match expected type: %s' % type_) # instead of str(type_) use a better description

		return s


	def _addSymbol(self, **kwargs): # fromTree=None, name=None, symbol=None
		if 'name' in kwargs:
			name = kwargs['name']
			fromTree = None
		else:
			fromTree = kwargs['fromTree']
			name = fromTree.text

		symbol = kwargs['symbol']

		# add a symbol to the innermost symbol table and makes sure that this symbol is unique
		if not name:
			name = fromTree.text

		prevDef = self._findSymbolHelper(name)

		if prevDef:
			# can only overload / overwrite functions
			if not isinstance(prevDef, list) or not isinstance(symbol, ESFunction):
				self._raiseException(RecoverableCompileError, tree=fromTree, inlineText='symbol already defined')


		for ast in reversed(self._nodes):
			st = getattr(ast, 'symbolTable', None)
			if not st:
				continue

			st.addSymbol(name, symbol)
			return

	def _createCastNode(self, exprNode, fromTypeName, toTypeName):
		# build an AST node like it would be created by the parser
		# esType information is added by the caller

		t = exprNode.copy(False) # copy line info
		t.type = TreeType.CAST
		t.text = u'CAST'

		t.addChild(exprNode.copy(True))
		t.addChild(Tree(fromTypeName))
		t.addChild(Tree(toTypeName))

		return t


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

		
		############################################
		# init some important data structures
		############################################
		self._initModuleSymbolTable()
		self._symbolTables = [ast.symbolTable]


		############################################
		# import stuff
		############################################
		#for x in statements:
		#	if x.type in [TreeType.IMPORTALL]:
		#		self._dispatch(x)

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
		

		esFunction = ESFunction(name.text, functionType, paramNames, mangling=mangling, linkage=linkage)
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

					# TODO insert CAST node



	def _onIntegerConstant(self, ast, constant):
		# FIXME really determine type of constant
		ast.esType = self._findSymbol(name=u'int32', type_=ESType)


	def _onBasicOperator(self, ast):
		nodeType = ast.text # FIXME use ast.type
		if ast.getChildCount() == 2 and nodeType in u'''* ** % / and xor or + - < <= == != >= >'''.split():
			self._dispatch(ast.children[0])
			self._dispatch(ast.children[1])

			left = ast.children[0]
			right = ast.children[1]

			esBool = self._findSymbol(name=u'bool', type_=ESType)

			if nodeType in u'* ** % / + -'.split():
				if left.esType.isEquivalentTo(right.esType, False):
					ast.esType = left.esType
				else:
					raise NotImplementedError('FIXME TODO')
			elif nodeType in u'and xor or'.split():
				#if left.esType.isEquivalentTo(right.esType, False) and left.esType.isEquivalentTo(esBool, False):
					ast.esType = esBool
				#else:
				#	raise NotImplementedError('FIXME TODO')
			elif nodeType in u'< <= == != >= >'.split():
				#if left.esType.isEquivalentTo(right.esType, False):
					ast.esType = esBool
				#else:
				#	raise NotImplementedError('FIXME TODO')
			else:
				raise NotImplementedError('FIXME TODO: %s' % nodeType)
		elif ast.getChildCount() == 1 and nodeType in u'''- + not'''.split():
			self._dispatch(ast.children[0])

			if nodeType in u'- +'.split():
				ast.esType = ast.children[0].esType
			elif nodeType == u'not':
				# TODO add implicit conversion to bool, if necessary
				ast.esType = self._findSymbol(name=u'bool', type_=ESType)
			else:
				assert(0 and 'dead code path')
		else:
			assert(0 and 'dead code path')


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

		ast.esType = returnTypes[0]


	def _onVariable(self, ast, variableName):
		s = self._findSymbol(fromTree=variableName, type_=ESVariable)

		ast.esType = s.esType

	def _onAssert(self, ast, expression):
		self._dispatch(expression)

		esType = expression.esType
		if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
			if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
				self._raiseException(RecoverableCompileError, tree=expression, inlineText='expression is of incompatible type. expected bool')

			# TODO insert CAST node

	def _onIf(self, ast, expressions, blocks, elseBlock):
		for x in expressions:
			self._dispatch(x)

		for i in range(len(expressions)):
			esType = expressions[i].esType

			if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
				if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
					self._raiseException(RecoverableCompileError, tree=expressions[i], inlineText='expression is of incompatible type. expected bool')

				# TODO insert CAST node

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






