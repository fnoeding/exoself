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


class ESVariable(object):
	def __init__(self, name, package, module, esType, storageClass='auto', linkage='default', mangling='default'):
		assert(isinstance(esType, ESType))
		self.name = name
		self.package = package
		self.module = module
		self._esType = esType # type can be modified by certain storage classes
		self.storageClass = storageClass
		self.linkage = linkage # only useful for global variables
		assert(mangling in ['default', 'C'])
		self.mangling = mangling


	def getESType(self):
		if self.storageClass == 'invariant':
			return self._esType.deriveInvariant()
		elif self.storageClass == 'const':
			return self._esType.deriveConst()
		elif self.storageClass == 'final':
			return self._esType.deriveConst()
		return self._esType


	def toLLVMType(self):
		# include things like storage class, linking etc
		return self.esType.toLLVMType()

	def __str__(self):
		return 'storage=%s linkage=%s %s as %s --> %s' % (self.storageClass, self.linkage, self.name, self.esType, self.llvmType)

	def isAssignable(self):
		if self.storageClass in ['invariant', 'const', 'final']:
			return False

		return True

		
	llvmType = property(toLLVMType)
	esType = property(getESType)


	def mangleName(self):
		if self.mangling == 'default':
			return self._mangleNameDefault()
		elif self.mangling == 'C':
			return self.name
		else:
			assert(0 and 'dead code path')


	def _mangleNameDefault(self):
		# header
		s = ['__ESG_']

		# package name: length of package name string, then package name
		s.append('%d%s' % (len(self.package), self.package))
		# module name: length of module name string, then module name
		s.append('%d%s' % (len(self.module), self.module))

		# visual separator, length of variable name string, then variable name and again visual separator
		s.append('__')
		s.append('%d%s' % (len(self.name), self.name))

		return ''.join(s)






