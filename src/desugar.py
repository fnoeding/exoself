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


from tree import Tree, TreeType



def _desugarLoopElse(tree):
	if not (tree.type == TreeType.WHILE and len(tree.children) == 3):
		return

	# transform a (WHILE (expr blockBody blockElse)) to (IF (expr (BLOCK (WHILE (expr blockBody)) blockElse)))

	# remove entries from top node
	tExprIf = tree.children[0]
	tExprWhile = tExprIf.copy(True)
	tBody = tree.children[1]
	tElse = tree.children[2]
	tree.children = []

	# create while node
	tWhile = tree.copy(False)
	tWhile.type = TreeType.WHILE
	tWhile.text = u'while'
	tWhile.addChild(tExprWhile)
	tWhile.addChild(tBody)

	# create block node
	tBlock = tree.copy(False)
	tBlock.type = TreeType.BLOCK
	tBlock.text = u'BLOCK'
	tBlock.addChild(tWhile)

	# create if node in place
	tree.type = TreeType.IF
	tree.text = u'if'
	tree.addChild(tExprIf)
	tree.addChild(tBlock)
	tree.addChild(tElse)


def _fixPackageAndModuleNames(tree):
	if tree.type == TreeType.PACKAGE or tree.type == TreeType.IMPORTALL:
		newText = [x.text for x in tree.children]
		del tree.children[1:]
		tree.children[0].text = u''.join(newText)


def _desugarMultiAssign(tree):
	# special action! we traverse the tree internally!
	assert(tree.type != TreeType.ASSIGN and 'desugaring of top level assignments is not possible. The assignment node MUST be a child node!')


	# transform assignments in the form
	#     a = b = c = expr;
	# to
	#     c = expr; b = c; a = b;
	# instead of
	#     c = expr; b = expr; a = expr;
	# this form avoids any problems related to already existing variables with different types


	i = 0
	while i < len(tree.children): # len must be calculated after every loop again!
		c = tree.children[i]
		if c.type == TreeType.ASSIGN and c.getChildCount() > 2:
			# fix this node

			# create new nodes
			nameNodes = c.children[:-1]
			exprNode = c.children[-1]

			nNames = len(nameNodes)
			newAssignNodes = []

			node = c.copy(False)
			node.children = [nameNodes[-1].copy(True), exprNode.copy(True)]
			newAssignNodes.append(node)

			for j in range(nNames - 2, -1, -1):# start with assignment on the right side working towards the left side
				variableNode = nameNodes[j + 1].copy(True)

				node = c.copy(False)
				node.children = [nameNodes[j].copy(True), variableNode]
				newAssignNodes.append(node)


			# now replace tree.children[i] with newAssignNodes
			a = tree.children[:i]
			b = tree.children[i + 1:]
			tree.children = a
			tree.children.extend(newAssignNodes)
			tree.children.extend(b)

			# do not skip ahead! then the assert below will check everything
			continue


		if c.text == u'=':
			assert(c.getChildCount() == 2)
		else:
			_desugarMultiAssign(c)
		i += 1


def _desugarNegativeNumberConstants(tree):
	# problem: numbers like -32768h are represented as a unary MINUS node and a INTEGER_CONSTANT node with type int16. But the 32768h is not a int16 number!

	if tree.type != TreeType.MINUS:
		return

	if len(tree.children) != 1:
		return

	if not tree.children[0].type in [TreeType.INTEGER_CONSTANT, TreeType.FLOAT_CONSTANT]:
		return

	# make a PLUS node out of this node, and move the sign into the constant
	tree.type = TreeType.PLUS
	tree.text = u'+'

	constNode = tree.children[0]
	valueNode = constNode.children[0]

	valueNode.text = '-' + valueNode.text # numbers are always positive!


def _desugarDereference(tree):
	# DEREFERENCE nodes must have at most 2 children: the pointer expression and optionally an offset

	if tree.type != TreeType.DEREFERENCE:
		return

	if len(tree.children) <= 2:
		return

	# x[3][2][1] gets parsed as (DEREFERENCE x 3 2 1)
	# and it must become (DEREFERENCE (DEREFERENCE (DEREFERENCE x, 3), 2), 1)

	pointer = tree.children[0]
	offsetsWithoutLast = tree.children[1:-1]
	lastOffset = tree.children[-1]

	tree.children = []

	current = tree.copy(False)
	current.children = [pointer, offsetsWithoutLast[0]]
	offsetsWithoutLast = offsetsWithoutLast[1:]
	while offsetsWithoutLast:

		new = tree.copy(False)
		new.children = [current, offsetsWithoutLast[0]]

		current = new
		offsetsWithoutLast = offsetsWithoutLast[1:]

	tree.children = [current, lastOffset]





# actions get called for every node
_actions = [_desugarLoopElse, _fixPackageAndModuleNames, _desugarNegativeNumberConstants, _desugarDereference]
# special actions traverse the tree themselves
_specialActions = [_desugarMultiAssign]

def _desugarActions(tree):
	for a in _actions:
		a(tree)

	for c in tree.children:
		_desugarActions(c)


	return tree


def desugar(tree):
	_desugarActions(tree)

	for sa in _specialActions:
		sa(tree)





