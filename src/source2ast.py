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
from lexer import Lexer
from parser import Parser
from tree import Tree, TreeType
from desugar import desugar


def antlrTree2Tree(antlrTree):
	t = Tree(antlrTree.type, antlrTree.text, antlrTree.line, antlrTree.charPositionInLine)

	for i in range(antlrTree.getChildCount()):
		subT = antlrTree2Tree(antlrTree.getChild(i))
		t.addChild(subT)

	return t


def sourcecode2AST(source, type='module'):
	# append additional NEWLINE at end of file
	source += '\n'

	inputStream = antlr3.ANTLRStringStream(source)
	lexer = Lexer(inputStream, source)
	tokens = antlr3.CommonTokenStream(lexer)
	#tokens.discardOffChannelTokens = True
	parser = Parser(tokens, source)

	assert type in ['module']
	if type == 'module':
		result = parser.start_module()

	# copy ast to our own tree implementation to make modifying easier
	astTree = antlrTree2Tree(result.tree)

	# 'desugar' it inplace
	desugar(astTree)

	return (parser.getNumberOfSyntaxErrors(), astTree)



def AST2StringAST(ast):
	return ast.toStringTree()

	r = ['']
	def walk(t, lvl):
		r.append((' ' * lvl) + repr(t.text))

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

	r = ['digraph G\n{']
	def walk(t, idGen):
		selfI = idGen.next()

		label = []
		label.append('<')
		label.append('<table border="0" cellborder="0" cellpadding="3" bgcolor="white">')

		label.append('<tr><td bgcolor="black" align="center" colspan="2"><font color="white">%s</font></td></tr>' % t.text) # FIXME use t.type as symbolic string

		def createRow(s1, s2=''):
			return '<tr><td align="left">%s</td><td align="left">%s</td></tr>' % (s1, s2)

		label.append(createRow('%s, %s' % (t.line, t.charPos)))

		label.append('</table>')
		label.append('>')

		label = ''.join(label)

		r.append('n%d [ label=%s, style="filled, bold" penwidth=5 fillcolor="white" shape="Mrecord" ];' % (selfI, label))
		#r.append('n%d [label="%s"];' % (selfI, t.text))

		n = t.getChildCount()
		for x in range(n):
			c = t.getChild(x)
			ci = walk(c, idGen)
			r.append('n%d -> n%d' % (selfI, ci))
		return selfI
	walk(ast, idGen())
	r.append('}')

	return '\n'.join(r)


def AST2PNG(ast):
	import subprocess

	dot = AST2DOT(ast)

	p = subprocess.Popen(['dot', '-Tpng'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

	p.stdin.write(dot)
	p.stdin.close()

	pngData = p.stdout.read()
	p.wait()

	return pngData










