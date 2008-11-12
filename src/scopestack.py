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


from esfunction import ESFunction
from esvariable import ESVariable
from estype import ESTypeOld as ESType



class ScopeStackWithProxy(object):
	def __init__(self, ss):
		self._ss = ss

	def __enter__(self):
		self._ss.pushScope()

	def __exit__(self, type, value, tb):
		self._ss.popScope()


class _ScopeStackEntries(object):
	def __init__(self):
		self._functions = {}
		self._variables = {}
		self._types = {}


	def add(self, name, x):
		r = self.find(name)

		if isinstance(x, ESVariable):
			assert(not r)
			self._variables[name] = x
		elif isinstance(x, ESType):
			assert(not r)
			self._types[name] = x
		elif isinstance(x, ESFunction):
			assert(r is None or isinstance(r, list))

			if r:
				self._functions[name].append(x)
			else:
				self._functions[name] = [x]
		else:
			assert(0 and 'dead code path')


	def find(self, name):
		if name in self._variables:
			return self._variables[name]

		if name in self._functions:
			r = self._functions[name]
			if not r:
				return None
			return r

		if name in self._types:
			return self._types[name]


		return None


	def findType(self, name):
		if name in self._types:
			return self._types[name]

		return None





class ScopeStack(object):
	def __init__(self):
		self._stack = {0: _ScopeStackEntries()}
		self._currentLevel = 0


	def popScope(self):
		assert(self._currentLevel > 0)

		del self._stack[self._currentLevel]
		self._currentLevel -= 1


	def pushScope(self):
		self._currentLevel += 1
		self._stack[self._currentLevel] = _ScopeStackEntries()


	def add(self, name, ref):
		r = self.find(name)
		if r and isinstance(r, list):
			assert(isinstance(ref, ESFunction))
			self._stack[self._currentLevel].add(name, ref)
		else:
			assert(not r)
			self._stack[self._currentLevel].add(name, ref)


	def find(self, name):
		results = []
		for i in range(self._currentLevel, -1, -1):
			r = self._stack[i].find(name)
			if not r:
				continue

			if isinstance(r, list):
				results.extend(r)
			else:
				return r

		return results


	def findType(self, name):
		for i in range(self._currentLevel, -1, -1):
			r = self._stack[i].findType(name)
			if r:
				return r

		return None


