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

from errors import CompileError, RecoverableCompileError
import os
from tree import TreeType



class ASTWalker(object):
	def __init__(self):
		dt = {}
		self._dispatchTable = dt
		self._nodes = [] # contains a list of all nodes starting with root node to current node; maintained by _dispatch



	def walkAST(self, ast, filename, sourcecode=''):
		assert(os.path.isabs(filename))
		self._filename = filename
		self._sourcecode = sourcecode
		self._sourcecodeLines = sourcecode.splitlines()

		self._dispatch(ast)

		return ast


	def _dispatch(self, ast):
		tt = TreeType
		kwargs = {}
		kwargs['ast'] = ast
		callee = None

		t = ast.type

		if t == tt.MODULESTART:
			callee = self._onModuleStart

			packageName = None
			moduleName = None
			
			n = len(ast.children)
			idx = 0
			for i in range(n):
				if ast.children[i].type == tt.PACKAGE:
					packageName = ast.children[i].children[0]
					idx += 1
				elif ast.children[i].type == tt.MODULE:
					moduleName = ast.children[i].children[0]
					idx += 1
			kwargs['statements'] = ast.children[idx:]
			kwargs['packageName'] = packageName
			kwargs['moduleName'] = moduleName
		elif t == tt.IMPORTALL:
			callee = self._onImportAll
			kwargs['moduleName'] = ast.children[0]
		elif t == tt.DEFFUNC:
			callee = self._onDefFunction

			n = len(ast.children)
			modifierKeys = []
			modifierValues = []
			for i in range(len(ast.children[0].children) // 2):
				modifierKeys.append(ast.children[0].children[2 * i])
				modifierValues.append(ast.children[0].children[2 * i + 1])
			kwargs['modifierKeys'] = modifierKeys
			kwargs['modifierValues'] = modifierValues

			kwargs['name'] = ast.children[1]
			kwargs['returnTypeName'] = ast.children[2]

			parameterNames = []
			parameterTypeNames = []
			for i in range(len(ast.children[3].children) // 2):
				parameterNames.append(ast.children[3].children[2 * i])
				parameterTypeNames.append(ast.children[3].children[2 * i + 1])
			kwargs['parameterNames'] = parameterNames
			kwargs['parameterTypeNames'] = parameterTypeNames

			if n == 4:
				block = None
			elif n == 5:
				block = ast.children[4]
			elif n > 5:
				assert(0 and 'dead code path')
			kwargs['block'] = block

		elif t == tt.BLOCK:
			callee = self._onBlock
			kwargs['blockContent'] = ast.children
		elif t == tt.PASS:
			callee = self._onPass
		elif t == tt.RETURN:
			callee = self._onReturn
			kwargs['expressions'] = ast.children
		elif t == tt.ASSERT:
			callee = self._onAssert
			kwargs['expression'] = ast.children[0]
		elif t == tt.IF:
			callee = self._onIf

			expressions = []
			blocks = []
			elseBlock = None
			for i in range(len(ast.children) // 2):
				expressions.append(ast.children[2 * i])
				blocks.append(ast.children[2 * i + 1])
			if len(ast.children) & 1:
				elseBlock = ast.children[-1]

			kwargs['expressions'] = expressions
			kwargs['blocks'] = blocks
			kwargs['elseBlock'] = elseBlock
		elif t == tt.FOR:
			callee = self._onFor
			kwargs['variableName'] = ast.children[0]

			rangeNode = ast.children[1]
			assert(rangeNode.type == tt.RANGE)
			rangeStart = None
			rangeStop = None
			rangeStep = None

			n = len(rangeNode.children)
			if n == 1:
				rangeStop = rangeNode.children[0]
			elif n == 2:
				rangeStart = rangeNode.children[0]
				rangeStop = rangeNode.children[1]
			elif n == 3:
				rangeStart = rangeNode.children[0]
				rangeStop = rangeNode.children[1]
				rangeStep = rangeNode.children[2]
			else:
				assert(0 and 'dead code path')

			kwargs['rangeStart'] = rangeStart
			kwargs['rangeStop'] = rangeStop
			kwargs['rangeStep'] = rangeStep

			kwargs['block'] = ast.children[2]
		elif t == tt.WHILE:
			callee = self._onWhile
			kwargs['expression'] = ast.children[0]
			kwargs['block'] = ast.children[1]
		elif t == tt.BREAK:
			callee = self._onBreak
		elif t == tt.CONTINUE:
			callee = self._onContinue
		elif t == tt.INTEGER_CONSTANT:
			callee = self._onIntegerConstant
			kwargs['constant'] = ast.children[0]
		elif t == tt.FLOAT_CONSTANT:
			callee = self._onFloatConstant
			kwargs['constant'] = ast.children[0]
		elif t == tt.CALLFUNC:
			callee = self._onCallFunc
			kwargs['calleeName'] = ast.children[0]
			kwargs['expressions'] = ast.children[1:]
		elif t == tt.VARIABLE:
			callee = self._onVariable
			kwargs['variableName'] = ast.children[0]
		elif t == tt.DEFVAR:
			callee = self._onDefVariable
			kwargs['variableName'] = ast.children[0]
			kwargs['typeName'] = ast.children[1]
		elif t == tt.ASSIGN:
			callee = self._onAssign
			kwargs['variableName'] = ast.children[0]
			kwargs['expression'] = ast.children[1]
		elif t == tt.LISTASSIGN:
			callee = self._onListAssign
			assert(len(ast.children[0].children) == len(ast.children[1].children))
			kwargs['variableNames'] = ast.children[0].children
			kwargs['expressions'] = ast.children[1].children
		elif t in [tt.PLUS, tt.MINUS, tt.STAR, tt.DOUBLESTAR, tt.SLASH, tt.PERCENT,
				tt.NOT, tt.AND, tt.OR, tt.XOR,
				tt.LESS, tt.LESSEQUAL, tt.EQUAL, tt.NOTEQUAL, tt.GREATEREQUAL, tt.GREATER]:
			# TODO
			callee = self._onBasicOperator
		else:
			assert(0 and 'dead code path / support for new token type not implemented')

		self._nodes.append(ast)
		try:
			return callee(**kwargs)
		finally:
			self._nodes.pop()

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
		



