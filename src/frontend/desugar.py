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





def _desugarLoopElse(tree):
	if not (tree.text == 'while' and len(tree.children) == 3):
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
	tWhile.text = 'while'
	tWhile.addChild(tExprWhile)
	tWhile.addChild(tBody)

	# create block node
	tBlock = tree.copy(False)
	tBlock.text = 'BLOCK'
	tBlock.addChild(tWhile)

	# create if node in place
	tree.text = 'if'
	tree.addChild(tExprIf)
	tree.addChild(tBlock)
	tree.addChild(tElse)



_actions = [_desugarLoopElse]


def desugar(tree):
	for a in _actions:
		a(tree)

	for c in tree.children:
		desugar(c)


	return tree





