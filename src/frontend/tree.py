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



class Tree(object):
	''' internal tree type used for AST storage instead of the antlr tree type '''
	def __init__(self, text, line=0, charPos=0):
		self.text = text
		self.children = []
		self.line = line
		self.charPos = 0


	def copy(self, copyChildren):
		t = Tree(self.text, self.line, self.charPos)

		if copyChildren:
			for x in self.children:
				t.children.append(x.copy(copyChildren))

		return t


	def getChildCount(self):
		return len(self.children)

	
	def getChild(self, i):
		return self.children[i]

	def addChild(self, t):
		self.children.append(t)


	def toStringTree(self):
		if not self.children:
			return self.text

		s = ['(', self.text, ' ']
		n = len(self.children)
		for i,x in enumerate(self.children):
			s.append(x.toStringTree())
			if i != n - 1:
				s.append(' ')
		s.append(')')

		return ''.join(s)
		






