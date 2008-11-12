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


elementaryTypes = {}
for i in [8, 16, 32, 64]:
	elementaryTypes[u'int%d' % i] = ESType([], ('elementary', 'int%d' % i))
	#elementaryTypes[u'uint%d' % i] = ESType([], ('elementary', 'uint%d' % i))
del i
elementaryTypes[u'bool'] = ESType([], ('elementary', 'bool'))
elementaryTypes[u'void'] = ESType([], ('elementary', 'void'))
elementaryTypes[u'single'] = ESType([], ('elementary', 'single'))
elementaryTypes[u'double'] = ESType([], ('elementary', 'double'))



implicitConversions = {}
def _buildImplicitConversionsTable():
	# bool to other
	l = []
	for x in u'int8 int16 int32 int64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'bool']] = l

	# int8 to other
	l = []
	for x in u'bool int16 int32 int64 single double'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int8']] = l

	# int16 to other
	l = []
	for x in u'bool int32 int64 single double'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int16']] = l


	# int32 to other
	l = []
	for x in u'bool int64 double'.split():# add single? that loses some precision but is at least consistent with the rules for int8, int16
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int32']] = l

_buildImplicitConversionsTable()


def canImplicitlyCast(fromType, toType):
	if not fromType in implicitConversions:
		return False

	l = implicitConversions[fromType]
	for x in l:
		if x.isEquivalentTo(toType, False):
			return True

	return False





