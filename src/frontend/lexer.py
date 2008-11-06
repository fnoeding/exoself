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

import antlr3
import exoselfLexer



class Lexer(exoselfLexer.exoselfLexer):
	def __init__(self, inputStream, source=None):
		exoselfLexer.exoselfLexer.__init__(self, inputStream)
		self._source = source
		if source:
			self._sourceLines = source.splitlines()
		else:
			self._sourceLines = None

	def nextToken(self):
		self.startPos = self.getCharPositionInLine()
		t = exoselfLexer.exoselfLexer.nextToken(self)
		return t

	def displayRecognitionError(self, tokenNames, e):
		if not e.line:
			s = 'line ???:???: lexer error\n'
		else:
			s = 'line %d:%d lexer error\n' % (e.line, e.charPositionInLine)

		s += '\t%s\n' % self.getErrorMessage(e, tokenNames)
		s += 'invocation stack: %s\n' % self.getRuleInvocationStack()

		self.emitErrorMessage(s)
		
	def getRuleInvocationStack(self):
		return self._getRuleInvocationStack(exoselfLexer.exoselfLexer.__module__)


