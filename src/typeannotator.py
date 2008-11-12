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
import estypesystem
from symboltable import SymbolTable


class ASTTypeAnnotator(astwalker.ASTWalker):
	def walkAST(self, ast, filename, sourcecode=''):
		assert(ast.text == 'MODULESTART')

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


	def _onModuleStart(self, ast):
		assert(ast.text == 'MODULESTART')

		self._moduleNode = ast
		self._symbolTables = []
		ast.symbolTable = None
		ast.packageName = ''
		ast.moduleName = None


		# get package and module statements
		idx = 0
		if ast.children[0].text in ['package', 'module']:
			self._dispatch(ast.children[0])
			idx += 1
		if ast.children[1].text in ['package', 'module']:
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
		#	if x.text in ['IMPORTALL']:
		#		self._dispatch(x)

		############################################
		# get global variables and functions
		############################################
		self._dispatchTable['DEFFUNC'] = '_onFuncPrototype'
		for x in ast.children:
			if x.text == 'DEFFUNC':
				self._dispatch(x) # do not directly call _onFuncPrototype; _dispatch manages _nodes field
		self._dispatchTable['DEFFUNC'] = '_onDefFunction'

		############################################
		# annotate the whole tree
		############################################
		for x in ast.children:
			if x.text in u'package module IMPORTALL'.split():
				# already done
				continue

			self._dispatch(x)



	def _onPackage(self, ast):
		assert(ast.text == 'package')

		self._moduleNode.packageName = ast.children[0].text


	def _onModule(self, ast):
		assert(ast.text == 'module')

		self._moduleNode.moduleName = ast.children[0].text


	def _onFuncPrototype(self, ast):
		assert(ast.text == 'DEFFUNC')


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
		assert(ast.text == 'DEFFUNC')

		if len(ast.children) == 4:
			# it's only a prototype
			return

		assert(len(ast.children) == 5)

		# add a new symbol table and add entries for parameter names
		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.

		esFunction = ast.esFunction
		esParamTypes = esFunction.esType.getFunctionParameterTypes()
		for i in range(len(esFunction.parameterNames)):
			self._addSymbol(name=esFunction.parameterNames[i], symbol=esParamTypes[i])

		blockNode = ast.children[4]
		self._dispatch(blockNode)


	def _onBlock(self, ast):
		assert(ast.text == 'BLOCK')

		ast.symbolTable = SymbolTable() # do not use directly! use self._addSymbol etc.	

		for x in ast.children:
			self._dispatch(x)

	
	def _onPass(self, ast):
		assert(ast.text == 'pass')


	def _onReturn(self, ast):
		assert(ast.text == 'return')

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
					self._raiseException(RecoverableCompileError, tree=ast.children[i], inlineText='incompatible return type')



	def _onIntegerConstant(self, ast):
		assert(ast.text == 'INTEGER_CONSTANT')

		# FIXME really determine type of constant
		ast.esType = self._findSymbol(name=u'int32', type_=ESType)


	def _onBasicOperator(self, ast):
		nodeType = ast.text
		if ast.getChildCount() == 2 and nodeType in u'''* ** % / and xor or + - < <= == != >= >'''.split():
			self._dispatch(ast.children[0])
			self._dispatch(ast.children[1])

			left = ast.children[0]
			right = ast.children[1]

			if nodeType in u'* ** % / + -'.split():
				if left.esType.isEquivalentTo(right.esType, False):
					ast.esType = left.esType
				else:
					raise NotImplementedError('FIXME TODO')
			elif nodeType in u'and xor or < <= == != >= >'.split():
				if left.esType.isEquivalentTo(right.esType, False):
					ast.esType = self.findSymbol(name=u'bool', type_=ESType)
				else:
					raise NotImplementedError('FIXME TODO')
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
		assert(ast.text == 'CALLFUNC')

		calleeNameNode = ast.children[0]
		argNodes = ast.children[1:]

		esFunctions = self._findSymbol(fromTree=calleeNameNode, type_=ESFunction)

		# TODO find best matching function for parameters
		# FIXME taking the first one for testing...
		assert(len(esFunctions) == 1)

		returnTypes = esFunctions[0].esType.getFunctionReturnTypes()
		assert(len(returnTypes) == 1)

		ast.esType = returnTypes[0]
	

