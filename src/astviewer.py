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


import pygtk
pygtk.require('2.0')
import gtk


class ASTViewer(object):
	def _deleteEvent(self, widget, event, data=None):
		gtk.main_quit()
		return False

	def __init__(self, ast, sourcecode=''):
		self._ast = ast
		self._sourcecode = sourcecode
		self._sourcecodeLines = sourcecode.splitlines()

		self._window = gtk.Dialog()
		self._window.set_title('Exoself AST Viewer')
		self._window.set_size_request(800, 600)
		
		self._window.connect('delete_event', self._deleteEvent)


		self._scrolledWindow = gtk.ScrolledWindow()
		self._scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self._window.vbox.pack_start(self._scrolledWindow, True, True, 0)




		cols = [str, str, str]
		headers = ['AST', 'source', 'esType']
		self._treeStore = gtk.TreeStore(*cols)
		self._treeView = gtk.TreeView(self._treeStore)
		tv = self._treeView

		for i in range(len(cols)):
			col = gtk.TreeViewColumn(headers[i])
			tv.append_column(col)

			cell = gtk.CellRendererText()
			col.pack_start(cell, True)
			col.add_attribute(cell, 'text', i)


		self._insertData()

		self._scrolledWindow.add_with_viewport(self._treeView)
		self._window.show_all()


	def _insertData(self):
		self._processAST(self._ast)


	def _processAST(self, ast, parent=None):

		l = []

		# text + texts of children
		if ast.children:
			s = []
			for c in ast.children:
				s.append(c.text)
			s = ', '.join(s)
			if len(s) > 50:
				s = s[0:25] + '... ...' + s[-25:]
			l.append('%s --> (%s)' % (ast.text, s))
		else:
			l.append(ast.text)

		# source, if available
		idx = ast.line - 1
		if 0 <= idx <= len(self._sourcecodeLines):
			l.append('% 5d: %s' % (ast.line, self._sourcecodeLines[idx]))
		else:
			l.append('% 5d' % ast.line)


		# es type, if available
		if hasattr(ast, 'esType'):
			l.append(str(ast.esType))
		else:
			l.append('')

		it = self._treeStore.append(parent, l)

		for c in ast.children:
			self._processAST(c, it)
		


def displayAST(ast, sourcecode=''):
	astV = ASTViewer(ast, sourcecode)
	gtk.main()



if __name__ == '__main__':
	import sys
	
	try:
		import cPickle as pickle
	except ImportError:
		import pickle

	f = file(sys.argv[1], 'r')
	ast = pickle.load(f)
	f.close()
	
	if len(sys.argv) > 1:
		sourcecode = file(sys.argv[2]).read()
	else:
		sourcecode = ''

	displayAST(ast, sourcecode)




