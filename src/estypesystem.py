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
elementaryTypes[u'float32'] = ESType([], ('elementary', 'float32'))
elementaryTypes[u'float64'] = ESType([], ('elementary', 'float64'))



implicitConversions = {}
def _buildImplicitConversionsTable():
	# (u)intN -> float32 / float64?
	# float32 has 23 bits mantissa --> information loss with int32, int64
	# float64 has 53 bits mantissa --> information loss with int64
	# but most of the time the result is really used as a floating point number, so it should be ok


	# bool to other
	l = []
	for x in u'int8 int16 int32 int64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'bool']] = l

	# int8 to other
	l = []
	for x in u'bool int16 int32 int64 float32 float64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int8']] = l

	# int16 to other
	l = []
	for x in u'bool int32 int64 float32 float64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int16']] = l

	# int32 to other
	l = []
	for x in u'bool int64 float32 float64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int32']] = l

	# int64 to other
	l = []
	for x in u'bool float32 float64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'int64']] = l

	# uint8 to other
	# uint16 to other
	# uint32 to other
	# uint64 to other

	# float32 to other
	l = []
	for x in u'bool float64'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'float32']] = l

	# float64 to other
	l = []
	for x in u'bool'.split():
		l.append(elementaryTypes[x])
	implicitConversions[elementaryTypes[u'float64']] = l


_buildImplicitConversionsTable()


def canImplicitlyCast(fromType, toType):
	assert(isinstance(fromType, ESType))
	assert(isinstance(toType, ESType))

	# any pointer can be implicitly cast to void*
	if fromType.isPointer and toType.isEquivalentTo(elementaryTypes[u'void'].derivePointer(), False):
		return True

	if not fromType in implicitConversions:
		return False

	l = implicitConversions[fromType]
	for x in l:
		if x.isEquivalentTo(toType, False):
			return True

	return False





