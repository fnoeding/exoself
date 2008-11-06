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
import exoselfParser


class Parser(exoselfParser.exoselfParser):
	def __init__(self, tokens, source=None):
		exoselfParser.exoselfParser.__init__(self, tokens)
		self._source = source
		if source:
			self._sourceLines = source.splitlines()
		else:
			self._sourceLines = None
	
	def displayRecognitionError(self, tokenNames, e):
		if not e.line:
			s = 'line ???:???:\n'
		else:
			s = 'line %d:%d parse error\n' % (e.line, e.charPositionInLine)

			# print some context
			if self._sourceLines:
				before = 3
				after = 3

				line = e.line - 1 # offset...

				i = line - before
				if i < 0:
					i = 0
				while i < line:
					s += '% 5d: %s\n' % (i + 1, self._sourceLines[i])
					i += 1
				
				s += '% 5d: %s\n' % (line + 1, self._sourceLines[line])
				s += ' ' * len('% 5d: ' % line)
				s += ' ' * e.charPositionInLine
				s += '^ ' + self.getErrorMessage(e, tokenNames)
				s += '\n'

				i = line + 1
				while i < len(self._sourceLines) and i < line + 1 + after:
					s += '% 5d: %s\n' % (i + 1, self._sourceLines[i])
					i += 1
			

		s += 'invocation stack: %s\n' % self.getRuleInvocationStack()

		self.emitErrorMessage(s)

	def getRuleInvocationStack(self):
		return self._getRuleInvocationStack(exoselfParser.exoselfParser.__module__)




