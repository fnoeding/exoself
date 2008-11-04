#!/usr/bin/python
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

from optparse import OptionParser
import sys

import antlr3
import exoselfLexer
import exoselfParser
import ast2llvm



class MyLexer(exoselfLexer.exoselfLexer):
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


	
class MyParser(exoselfParser.exoselfParser):
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






def sourcecode2AST(source, type='module'):
	# append additional NEWLINE at end of file
	source += '\n'

	inputStream = antlr3.ANTLRStringStream(source)
	lexer = MyLexer(inputStream, source)
	tokens = antlr3.CommonTokenStream(lexer)
	#tokens.discardOffChannelTokens = True
	parser = MyParser(tokens, source)

	assert type in ['module']
	if type == 'module':
		result = parser.start_module()

	return (parser.getNumberOfSyntaxErrors(), result.tree)



def AST2StringAST(ast):
	return ast.toStringTree()

	r = ['']
	def walk(t, lvl):
		r.append((' ' * lvl) + repr(t.getText()))

		n = t.getChildCount()
		for x in range(n):
			c = t.getChild(x)
			walk(c, lvl + 1)

	walk(ast, 0)
	return '\n'.join(r)



def AST2DOT(ast):
	def idGen():
		i = 0
		while True:
			yield i
			i += 1

	r = ['graph G\n{']
	def walk(t, idGen):
		selfI = idGen.next()
		r.append('n%d [label="%s"];' % (selfI, t.getText()))

		n = t.getChildCount()
		for x in range(n):
			c = t.getChild(x)
			ci = walk(c, idGen)
			r.append('n%d -- n%d' % (selfI, ci))
		return selfI
	walk(ast, idGen())
	r.append('}')

	return '\n'.join(r)



def main():
	# setup option parser
	optparser = OptionParser()
	optparser.add_option('-o', '--output', dest='astOutput', default='-')
	optparser.add_option('-d', '--dot-output', dest='dotOutput', default=None)
	optparser.add_option('-r', '--run', dest='run', default=False, action="store_true")

	# get options
	options, args = optparser.parse_args()

	# get source
	if len(args) == 0:
		source = sys.stdin.read()
	else:
		source = file(args[0]).read()
	
	# transform to AST
	numErrors, ast = sourcecode2AST(source)
	if numErrors:
		print >> sys.stderr, 'errors occured while parsing'
		return 1

	if options.astOutput == '-':
		sys.stdout.write(AST2StringAST(ast))
	else:
		f = file(options.astOutput, 'w')
		f.write(AST2StringAST(ast))
		f.close()

	if options.dotOutput:
		f = file(options.dotOutput, 'w')
		f.write(AST2DOT(ast))
		f.close()

	if options.run:
		mt = ast2llvm.ModuleTranslator()
		module, functions = mt.translateAST(ast)

		print '\n\ntranslation result'
		print module

		print 'running main function:'
		ast2llvm.run(module, functions['main'])


	
	return 0






if __name__ == '__main__':
	sys.exit(main())



