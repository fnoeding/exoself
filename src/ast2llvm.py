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

import copy

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




class ModuleTranslator(object):
	def __init__(self):
		self._dispatchTable = {}
		self._dispatchTable['MODULE'] = self._onModule
		self._dispatchTable['DEFFUNC'] = self._onDefFunction
		self._dispatchTable['BLOCK'] = self._onBlock
		self._dispatchTable['pass'] = self._onPass
		self._dispatchTable['return'] = self._onReturn
		self._dispatchTable['assert'] = self._onAssert
		self._dispatchTable['if'] = self._onIf
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


	def _onModule(self, tree):
		assert(tree.getText() == 'MODULE')

		self._module = Module.new('main_module')
		self._scopeStack = _ScopeStack()

		# first pass: make all functions available, so we don't need any stupid forward declarations
		for x in _childrenIterator(tree):
			if x.getText() == 'DEFFUNC':
				self._onDefProtoype(x)


		# second pass: translate code
		for x in _childrenIterator(tree):
			self._dispatch(x)


	def _onDefProtoype(self, tree):
		# this function also gets called for functions definitions and should then only generate a prototype
		assert(tree.getText() == 'DEFFUNC')


		ci = _childrenIterator(tree)
		name = ci.next().getText()
		returnType = ci.next().getText()
		argList = ci.next()

		if returnType == 'int32':
			ty_ret = Type.int(32)
		elif returnType == 'void':
			ty_ret = Type.void()
		else:
			raise NotImplementedError('unsupported type: %s' % returnType)


		functionParam_ty = []
		functionParamNames = []
		for i in range(argList.getChildCount() / 2):
			argName = argList.getChild(i * 2).getText()
			argTypeName = argList.getChild(i * 2 + 1).getText()

			if argTypeName == 'int32':
				arg_ty = Type.int(32)
			else:
				raise NotImplementedError('unsupported type: %s' % typeName)

			functionParam_ty.append(arg_ty)
			functionParamNames.append(argName)


		ty_funcProto = Type.function(ty_ret, functionParam_ty)

		# was there already a function with this name?
		# if everything matches, just ignore - otherwise fail
		if name in self._functions:
			ty_old_func = self._functions[name]

			# compare types
			assert(ty_old_func.type == Type.pointer(ty_funcProto))

			# TODO compare more?
			# maybe add argument names if they were omitted previously?
		else:
			ty_func = self._module.add_function(ty_funcProto, name)

			for i,x in enumerate(functionParamNames):
				ty_func.args[i].name = x

			self._functions[name] = ty_func # FIXME refactor: this dict is also provided by module


	def _onDefFunction(self, tree):
		assert(tree.getText() == 'DEFFUNC')

		ci = _childrenIterator(tree)
		name = ci.next().getText()
		returnType = ci.next().getText()
		argList = ci.next()

		self._onDefProtoype(tree)
		ty_func = self._functions[name]
		ty_func.name = name

		# differentiate between declarations and definitions
		if tree.getChildCount() == 3:
			# declaration
			return
	
		with _ScopeStackWithProxy(self._scopeStack):

			self._currentFunction = ty_func
			self._functions[name] = ty_func
			entryBB = ty_func.append_basic_block('entry')

			# add variables
			for i in range(len(ty_func.args)):
				#self._scopeStack.add(ty_func.args[i].name, ty_func.args[i])
				self._createAllocaForVar(ty_func.args[i].name, ty_func.args[i].type, ty_func.args[i])


			addedBRToEntryBB = False
			for x in ci:
				currentBB = ty_func.append_basic_block('bb')
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
					print 'control flow possibly reaches end of non-void function. Inserting trap instruction...'
					trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
					self._currentBuilder.call(trapFunc, [])
					self._currentBuilder.ret(Constant.int(Type.int(32), -1)) # and return, otherwise ty_func.verify will fail
					
				

			ty_func.verify()


	def _onBlock(self, tree):
		assert(tree.getText() == 'BLOCK')

		for x in _childrenIterator(tree):
			self._dispatch(x)



	def _onReturn(self, tree):
		assert(tree.getText() == 'return')

		value = self._dispatch(tree.getChild(0))
		self._currentBuilder.ret(value)

	def _onAssert(self, tree):
		assert(tree.getText() == 'assert')

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
		trapFunc = Function.intrinsic(self._module, INTR_TRAP, []);
		thenBuilder.call(trapFunc, [])
		thenBuilder.branch(elseBB) # we'll never get here - but create proper structure of IR
	
		self._currentBuilder = Builder.new(elseBB)

	def _onIf(self, tree):
		assert(tree.getText() == 'if')
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


	def _onVariable(self, tree):
		assert(tree.getText() == 'VARIABLE')

		varName = tree.getChild(0).getText()
		ref = self._scopeStack.find(varName)
		assert(ref and 'variable was not defined: %s' % varName)

		#return ref

		return self._currentBuilder.load(ref)


	def _createAllocaForVar(self, name, type, value=None):
		assert(not isinstance(type, str))

		if type == Type.int(32):
			defaultValue = Constant.int(type, 0)
		else:
			assert(0 and 'unsupported variable type: %s' % type)

		if value == None:
			value = defaultValue

		# check if this variable is already defined
		assert(not self._scopeStack.find(name) and 'variable already defined: %s' % name)

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


	def _onDefVariable(self, tree):
		assert(tree.getText() == 'DEFVAR')

		varName = tree.getChild(0).getText()
		varType = tree.getChild(1).getText()

		if varType == 'int32':
			varType = Type.int(32)
		else:
			assert(0 and 'unsuported variable type')

		self._createAllocaForVar(varName, varType)


	def _onCallFunc(self, tree):
		assert(tree.getText() == 'CALLFUNC')

		ci = _childrenIterator(tree)
		callee = ci.next().getText()
		assert(callee in self._functions and 'function not found')

		params = []
		for x in ci:
			r = self._dispatch(x)
			params.append(r)

		return self._currentBuilder.call(self._functions[callee], params, 'ret_%s' % callee)

	def _onBasicOperator(self, tree):
		nodeType = tree.getText()
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
				ty_int = Type.int(32)
				return self._currentBuilder.sub(Constant.int(ty_int, 0), v1)
			elif nodeType == 'not':
				r = self._currentBuilder.icmp(IPRED_EQ, v1, Constant.int(v1.type, 0))

				return self._currentBuilder.zext(r, Type.int(32))
			else:
				assert(0 and 'dead code path')
		else:
			raise NotImplementedError('basic operator \'%s\' not yet implemented' % nodeType)

	def _simpleAssignment(self, name, value):
		ref = self._scopeStack.find(name)
		if ref:
			# variable already exists
			self._currentBuilder.store(value, ref)
		else:
			# new variable
			# do not pass value when creating the variable! The value is NOT available in the entry block (at least in general)!
			self._createAllocaForVar(name, value.type)

			ref = self._scopeStack.find(name)
			self._currentBuilder.store(value, ref)
		
		return ref

	def _onAssign(self, tree):
		assert(tree.getText() == '=')

		n = tree.getChildCount()
		names = []
		for i in range(n - 1):
			names.append(tree.getChild(i).getText())

		value = self._dispatch(tree.getChild(n - 1))

		# transform assignments in the form
		#     a = b = c = expr;
		# to
		#     c = expr; b = c; a = b;
		# instead of
		#     c = expr; b = expr; a = expr;
		# this form avoids any problems related to already existing variables with different types

		lastResult = value;
		for name in names:
			ref = self._simpleAssignment(name, lastResult)

			if ref.type != lastResult.type:# when we get different types this gets finally called and must do some conversions
				lastResult = self._currentBuilder.load(ref)


		return lastResult # TODO really needed?

	def _onListAssign(self, tree):
		assert(tree.getText() == 'LISTASSIGN')

		lhs = tree.getChild(0)
		assert(lhs.getText() == 'ASSIGNLIST')
		rhs = tree.getChild(1)
		assert(rhs.getText() == 'ASSIGNLIST')

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
			destination = lhs.getChild(i).getText()

			self._simpleAssignment(destination, value)




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



