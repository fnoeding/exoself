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


	def _onModuleStart(self, ast):
		self._moduleNode = ast
		self._symbolTables = []
		ast.symbolTable = None
		ast.packageName = ''
		ast.moduleName = None

		# get package and module statements
		idx = 0
		if len(ast.children) > 0 and ast.children[0].type in [TreeType.PACKAGE, TreeType.MODULE]:
			self._dispatch(ast.children[0])
			idx += 1
		if len(ast.children) > 1 and ast.children[1].type in [TreeType.PACKAGE, TreeType.MODULE]:
			self._dispatch(ast.children[1])
			idx += 1

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
		#for x in ast.children[idx:]:
		#	if x.type in [TreeType.IMPORTALL]:
		#		self._dispatch(x)

		############################################
		# get global variables and functions
		############################################
		old = self._onDefFunction
		self._onDefFunction = self._onFuncPrototype
		for x in ast.children:
			if x.type == TreeType.DEFFUNC:
				self._dispatch(x) # do not directly call _onFuncPrototype; _dispatch manages _nodes field
		self._onDefFunction = old

		############################################
		# annotate the whole tree
		############################################
		for x in ast.children:
			if x.type in [TreeType.PACKAGE, TreeType.MODULE, TreeType.IMPORTALL]:
				# already done
				continue

			self._dispatch(x)



	def _onPackage(self, ast):
		self._moduleNode.packageName = ast.children[0].text


	def _onModule(self, ast):
		self._moduleNode.moduleName = ast.children[0].text


	def _onFuncPrototype(self, ast):
		modifiers = ast.children[0]
		functionNameNode = ast.children[1]
		functionName = functionNameNode.text
		returnTypeNode = ast.children[2]
		parameters = ast.children[3]
		# optional 5th part 'block' is not needed here

		# create type of function
		returnTypes = [self._findSymbol(fromTree=returnTypeNode, type_=ESType)]

		parameterNames = []
		parameterTypes = []
		for i in range(len(parameters.children) // 2):
			name = parameters.children[i * 2].text
			typeNameNode = parameters.children[i * 2 + 1]

			parameterNames.append(name)
			type_ = self._findSymbol(fromTree=typeNameNode, type_=ESType)

			parameterTypes.append(type_)

		functionType = ESType.createFunction(returnTypes, parameterTypes)


		# parse modifiers
		linkage = None
		mangling = None
		for i in range(len(modifiers.children) // 2):
			name = modifiers.children[i * 2].text
			value = modifiers.children[i * 2 + 1].text

			if name == u'linkage':
				linkage = value
			elif name == u'mangling':
				mangling = value
			else:
				self._raiseException(RecoverableCompileError, tree=modifiers.children[i * 2 +1], inlineText='unknown function modifier')
		

		esFunction = ESFunction(functionName, functionType, parameterNames, mangling=mangling, linkage=linkage)
		ast.esFunction = esFunction

		# TODO check for duplicate entries
		self._addSymbol(fromTree=functionNameNode, symbol=esFunction)


	def _onDefFunction(self, ast):
		if len(ast.children) == 4:
			# it's only a prototype
			return

		assert(len(ast.children) == 5)

		# add a new symbol table and add entries for parameter names
		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.

		esFunction = ast.esFunction
		esParamTypes = esFunction.esType.getFunctionParameterTypes()
		for i in range(len(esFunction.parameterNames)):
			varName=esFunction.parameterNames[i]
			esVar = ESVariable(varName, esParamTypes[i])
			self._addSymbol(name=varName, symbol=esVar)

		blockNode = ast.children[4]
		self._dispatch(blockNode)


	def _onBlock(self, ast):
		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.	

		for x in ast.children:
			self._dispatch(x)

	
	def _onPass(self, ast):
		pass


	def _onReturn(self, ast):
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
			if len(ast.children) > 0:
				self._raiseException(RecoverableCompileError, tree=ast, inlineText='function is declared as void: can\'t return anything')

		else:
			for i, x in enumerate(ast.children):
				self._dispatch(x)
				t = x.esType # every expression must have an esType member

				# FIXME provide implicit conversion support 
				if not t.isEquivalentTo(returnTypes[i], False):
					# types did not match, try implicit cast
					if not estypesystem.canImplicitlyCast(t, returnTypes[i]):
						self._raiseException(RecoverableCompileError, tree=ast.children[i], inlineText='incompatible return type')

					# TODO insert CAST node



	def _onIntegerConstant(self, ast):
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


	def _onCallFunc(self, ast):
		calleeNameNode = ast.children[0]
		argNodes = ast.children[1:]

		esFunctions = self._findSymbol(fromTree=calleeNameNode, type_=ESFunction)

		# TODO find best matching function for parameters
		# FIXME taking the first one for testing...
		assert(len(esFunctions) == 1)

		returnTypes = esFunctions[0].esType.getFunctionReturnTypes()
		assert(len(returnTypes) == 1)

		ast.esType = returnTypes[0]


	def _onVariable(self, ast):
		varNameNode = ast.children[0]	


		s = self._findSymbol(fromTree=varNameNode, type_=ESVariable)

		ast.esType = s.esType

	def _onAssert(self, ast):
		self._dispatch(ast.children[0])

		esType = ast.children[0].esType
		if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
			if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
				self._raiseException(RecoverableCompileError, tree=ast.children[0], inlineText='expression is of incompatible type. expected bool')

			# TODO insert CAST node

	def _onIf(self, ast):
		# dispatch all nodes
		for x in ast.children:
			self._dispatch(x)

		n = len(ast.children)
		for i in range(n // 2):
			exprNode = ast.children[2 * i]
			esType = exprNode.esType

			if not esType.isEquivalentTo(self._findSymbol(name=u'bool', type_=ESType), False):
				if not estypesystem.canImplicitlyCast(esType, self._findSymbol(name=u'bool', type_=ESType)):
					self._raiseException(RecoverableCompileError, tree=ast.children[0], inlineText='expression is of incompatible type. expected bool')

				# TODO insert CAST node


	def _onDefVariable(self, ast):
		varNameNode = ast.children[0]
		varTypeNameNode = ast.children[1]

		esType = self._findSymbol(fromTree=varTypeNameNode, type_=ESType)
		esVar = ESVariable(varNameNode.text, esType)
		self._addSymbol(fromTree=varNameNode, symbol=esVar)


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


	
	def _onAssign(self, ast):
		varNameNode = ast.children[0]
		exprNode = ast.children[1]


		self._onAssignHelper(varNameNode, exprNode)


	def _onListAssign(self, ast):
		# semantics of list assign in cases where a variable is referenced on both sides:
		# 1st copy results of ALL expressions into temporary variables
		# 2nd copy content of temporary variables to destination variables
		# --> just assign esType of n-th expression to n-th assignee

		destinationNameNodes = ast.children[0].children
		exprNodes = ast.children[1].children

		assert(len(destinationNameNodes) == len(exprNodes))

		for i in range(len(exprNodes)):
			self._onAssignHelper(destinationNameNodes[i], exprNodes[i])


	def _onFor(self, ast):
		ast.symbolTable = SymbolTable() # do not use directly!

		varNameNode = ast.children[0]
		assert(ast.children[1].type == TreeType.RANGE)

		rangeNode = ast.children[1]
		blockNode = ast.children[2]

		n = len(rangeNode.children)
		if n == 3:
			startExprNode = rangeNode.children[0]
			stopExprNode = rangeNode.children[1]
			stepExprNode = rangeNode.children[2]

			self._dispatch(startExprNode)
			self._dispatch(stopExprNode)
			self._dispatch(stepExprNode)
		elif n == 2:
			startExprNode = rangeNode.children[0]
			stopExprNode = rangeNode.children[1]
			stepExprNode = None
			
			self._dispatch(startExprNode)
			self._dispatch(stopExprNode)
		elif n == 1:
			startExprNode = None
			stopExprNode = rangeNode.children[0]
			stepExprNode = None

			self._dispatch(stopExprNode)
		else:
			assert(0 and 'dead code path')


		# FIXME for now only int32 support
		int32 = self._findSymbol(name=u'int32', type_=ESType)
		bad = False
		if startExprNode and not startExprNode.esType.isEquivalentTo(int32, False):
			bad = True
		if stopExprNode and not stopExprNode.esType.isEquivalentTo(int32, False):
			bad = True
		if stepExprNode and not stepExprNode.esType.isEquivalentTo(int32, False):
			bad = True

		if bad:
			self._raiseException(RecoverableCompileError, tree=rangeNode, inlineText='range expressions are currently only implemented for int32')

		try:
			var = self._findSymbol(fromTree=varNameNode, type_=ESVariable)
		except CompileError:
			var = None

		if var:
			if not var.esType.isEquivalentTo(int32, False):
				self._raiseException(RecoverableCompileError, tree=varNameNode, inlineText='loop variable must be of type int32 until support for other types is implemented')
		else:
			var = ESVariable(varNameNode.text, int32)
			self._addSymbol(fromTree=varNameNode, symbol=var)
			
		self._dispatch(blockNode)


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


	def _onWhile(self, ast):
		exprNode = ast.children[0]
		self._dispatch(exprNode)

		esType = exprNode.esType
		bool = self._findSymbol(name=u'bool', type_=ESType)
		if not esType.isEquivalentTo(bool, False):
			# types did not match, try implicit cast
			if not estypesystem.canImplicitlyCast(esType, bool):
				self._raiseException(RecoverableCompileError, tree=ast.children[i], inlineText='incompatible type, expected bool')

			# TODO add cast node


		self._dispatch(ast.children[1])






