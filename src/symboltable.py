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
from estype import ESType
from esvariable import ESVariable
from esfunction import ESFunction


class SymbolTable(object):
	def __init__(self):
		self._symbols = {} # maps names to symbols
		self._aliases = {} # maps names to names


	def addSymbol(self, name, symbol):
		assert(isinstance(name, unicode))
		assert(isinstance(symbol, (ESType, ESVariable, ESFunction)))

		if isinstance(symbol, ESFunction):
			# due to function overloading support any number of functions with the same name
			baseName = self.findBaseName(name)

			if baseName:
				assert(isinstance(self._symbols[baseName], list))
				self._symbols[baseName].append(symbol)
			else:
				self._symbols[name] = [symbol]
		else:
			# no overwriting!
			assert(not self.findBaseName(name))

			self._symbols[name] = symbol

	def getAllSymbols(self):
		return self._symbols.copy() # shallow copy should be enough


	def findBaseName(self, name):
		assert(isinstance(name, unicode))

		while name in self._aliases:
			name = self._aliases[name]

		if name in self._symbols:
			return name
		return None


	def findSymbol(self, name):
		assert(isinstance(name, unicode))

		baseName = self.findBaseName(name)
		if not baseName:
			return None
		
		return self._symbols[baseName]


	def addAlias(self, oldName, newName):
		assert(isinstance(oldName, unicode))
		assert(isinstance(newNawe, unicode))
		assert(oldName in self._types or oldName in self._aliases)
		assert(not self.findBaseName(newName))

		# in principle we could add a direct entry to the base name. But then we lose the information how the alias was defined
		# if it's too slow just add another dict with direct mappings for general use
		self._aliases[newName] = oldName


	def __str__(self):
		s = []
		s.append('symbols')
		for k, v in self._symbols.items():
			if isinstance(v, list):
				s.append(k)
				for x in v:
					s.append('\t--> %s' % x)
			else:
				s.append('%s --> %s' % (k, v))
		s.append('aliases')
		for k, v in self._aliases.items():
			s.append('%s --> %s' % (k, v))
		return '\n'.join(s)
			



