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


from estype import ESType


class ESFunction(object):
	def __init__(self, name, package, module, esType, paramNames, mangling=None, linkage=None):
		assert(isinstance(name, unicode))
		assert(isinstance(esType, ESType))
		for x in paramNames:
			assert(isinstance(x, unicode))

		self.esType = esType
		self.name = name
		self.package = package
		self.module = module
		self.parameterNames = paramNames
		# the llvm backend adds a member llvmRef here

		if not mangling:
			mangling = 'default'
		assert(mangling in ['default', 'C'])
		self.mangling = mangling

		if not linkage:
			linkage = 'default'
		assert(linkage in ['default', 'extern'])
		self.linkage = linkage


	def _mangleNameDefault(self):
		# header
		s = ['__ESF_']
		# package name: length of package name string, then package name
		s.append('%d%s' % (len(self.package), self.package))
		# module name: length of module name string, then module name
		s.append('%d%s' % (len(self.module), self.module))

		# visual separator, length of function name string, then function name and again visual separator
		s.append('__')
		s.append('%d%s' % (len(self.name), self.name))
		s.append('__')

		# function signature
		s.append(self.esType.mangleName('default'))

		return ''.join(s)


	def mangleName(self):
		if self.name == 'main':
			return '__ES_main'


		if self.mangling == 'default':
			return self._mangleNameDefault()
		elif self.mangling== 'C':
			return self.name
		else:
			assert(0 and 'dead code path')


	def __str__(self):
		return '%s (%s, %s): %s; linkage=%s mangling=%s' % (self.name, self.package, self.module, self.esType, self.linkage, self.mangling)


	mangledName = property(mangleName)



