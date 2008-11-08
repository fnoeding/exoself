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

from llvm.core import *


class ScopeStackWithProxy(object):
	def __init__(self, ss):
		self._ss = ss

	def __enter__(self):
		self._ss.pushScope()

	def __exit__(self, type, value, tb):
		self._ss.popScope()



class ScopeStack(object):
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


	def add(self, name, ref):
		if ref.type.pointee.kind == TYPE_FUNCTION:
			# there may be several functions using the same name
			# --> function overloading

			# check that there is no variable shadowing that would shadow this function
			r = self.find(name)
			if not r:
				self._stack[self._currentLevel][name] = [ref]
			else:
				assert(type(r) == list and 'trying to shadow a variable with a function name')

				# do NOT use r to append!
				if name in self._stack[self._currentLevel]:
					self._stack[self._currentLevel][name].append(ref)
				else:
					self._stack[self._currentLevel][name] = [ref]
		else:
			assert(not self.find(name))

			self._stack[self._currentLevel][name] = ref


	def find(self, name):
		results = []

		for x in range(self._currentLevel, -1, -1):
			m = self._stack[x]

			try:
				v = m[name]
			except:
				continue

			if type(v) == list:
				# function
				results.extend(v)
			else:
				return v


		if results:
			return results
		else:
			return None

