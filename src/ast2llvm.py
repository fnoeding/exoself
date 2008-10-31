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

from llvm import *
from llvm.core import *
from llvm.ee import *


def _childrenIterator(tree):
	n = tree.getChildCount()
	for i in range(n):
		yield tree.getChild(i)


class ModuleTranslator(object):
	def __init__(self):
		self._dispatchTable = {}
		self._dispatchTable['MODULE'] = self._onModule
		self._dispatchTable['DEFFUNC'] = self._onDefFunction
		self._dispatchTable['BLOCK'] = self._onBlock
		self._dispatchTable['pass'] = self._onPass
		self._dispatchTable['return'] = self._onReturn
		self._dispatchTable['INTEGER_CONSTANT'] = self._onIntegerConstant
		self._dispatchTable['FLOAT_CONSTANT'] = self._onFloatConstant
		self._dispatchTable['+'] = self._onBasicMathOperator
		self._dispatchTable['-'] = self._onBasicMathOperator
		self._dispatchTable['*'] = self._onBasicMathOperator
		self._dispatchTable['/'] = self._onBasicMathOperator
		self._dispatchTable['//'] = self._onBasicMathOperator
		self._dispatchTable['%'] = self._onBasicMathOperator



	def _onModule(self, tree):
		assert(tree.getText() == 'MODULE')

		self._module = Module.new('main_module')

		for x in _childrenIterator(tree):
			self._dispatch(x)


	def _onDefFunction(self, tree):
		assert(tree.getText() == 'DEFFUNC')

		ci = _childrenIterator(tree)
		name = ci.next().getText()
		returnType = ci.next().getText()

		if returnType == 'int32':
			ty_ret = Type.int(32)
		elif returnType == 'void':
			ty_ret = Type.void()
		else:
			raise NotImplementedError('unsupported type: %s' % returnType)

		ty_funcProto = Type.function(ty_ret, [])
		ty_func = self._module.add_function(ty_funcProto, name)

		self._currentFunction = ty_func
		self._functions[name] = ty_func

		for x in ci:
			self._currentBB = ty_func.append_basic_block('entry')
			self._currentBuilder = Builder.new(self._currentBB)
			
			self._onBlock(x)

		if returnType == 'void':
			self._currentBuilder.ret_void()

		ty_func.verify()

	def _onBlock(self, tree):
		assert(tree.getText() == 'BLOCK')

		for x in _childrenIterator(tree):
			self._dispatch(x)



	def _onReturn(self, tree):
		assert(tree.getText() == 'return')

		value = self._dispatch(tree.getChild(0))
		self._currentBuilder.ret(value)


	def _onPass(self, tree):
		assert(tree.getText() == 'pass')
		# nothing to do here

	def _onIntegerConstant(self, tree):
		assert(tree.getText() == 'INTEGER_CONSTANT')

		value = tree.getChild(0).getText().replace('_', '').lower()

		if value.startswith('0x'):
			i = int(value[2:], 16)
		elif value.startswith('0b'):
			i = int(value[2:], 2)
		elif value.startswith('0') and len(value) > 1:
			i = int(value[1:], 8)
		else:
			i = int(value)
		

		ty_int = Type.int(32)

		return Constant.int(ty_int, i)


	def _onFloatConstant(self, tree):
		assert(tree.getText() == 'FLOAT_CONSTANT')

		value = tree.getChild(0).getText().replace('_', '').lower()
		
		f = float(value)

		ty_float = Type.float()

		return Constant.real(ty_float, f) # FIXME use float


	def _onBasicMathOperator(self, tree):
		nodeType = tree.getText()
		if nodeType in ['*', '//', '%', '/'] or (tree.getChildCount() == 2 and nodeType in ['+', '-']):
			first = tree.getChild(0)
			second = tree.getChild(1)

			v1 = self._dispatch(first)
			v2 = self._dispatch(second)

			if nodeType == '*':
				return self._currentBuilder.mul(v1, v2)
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
			else:
				assert('should never get here')
		elif tree.getChildCount() == 1 and nodeType in ['-', '+']:
			v1 = self._dispatch(tree.getChild(0))

			if nodeType == '+':
				return v1
			elif nodeType == '-':
				ty_int = Type.int(32)
				return self._currentBuilder.sub(Constant.int(ty_int, 0), v1)
		else:
			raise NotImplementedError('basic math operator \'%s\' not yet implemented' % nodeType)



	def _dispatch(self, tree):
		return self._dispatchTable[tree.getText()](tree)



	def translateAST(self, tree):
		assert(tree.getText() == 'MODULE')

		self._module = None
		self._functions = {}
		

		self._dispatch(tree)

		self._module.verify()

		return self._module, self._functions


def run(module, function):
	mp = ModuleProvider.new(module)
	ee = ExecutionEngine.new(mp)

	return ee.run_function(function, [])



