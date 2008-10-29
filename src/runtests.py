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


import os
import sys
from optparse import OptionParser



def runTest(filebase):
	# convert source 2 ast
	ast = os.popen('./source2ast.py %s.es' % filebase, 'r').read()
	# check ast
	if os.path.exists('%s.ast' % filebase):
		expectedAST = file('%s.ast' % filebase).read()
		expectedAST = ' '.join(expectedAST.split('\n'))
		if ast.strip() != expectedAST.strip():
			print 'received: %s\nexpected: %s' % (ast, expectedAST)
			return False

	else:
		print 'no reference! received: %s' % ast

	# run code and test result
	# TODO

	return True


def main():
	parser = OptionParser()
	parser.add_option('-s', '--suite', help='test suite prefix', dest='suitePrefix')
	parser.add_option('-k', '--continue', help='continue even when tests fail', dest='continueAfterFailure', action='store_true', default=False)

	options, args = parser.parse_args()

	total = 0
	failed = 0

	halt = False

	l = os.listdir('../tests')
	l.sort()
	for e in l:
		e = '../tests/' + e
		if os.path.isdir(e):
			print e

			l2 = os.listdir(e)
			l2.sort()
			for x in l2:
				if not x.endswith('.es'):
					continue
				x = '%s/%s' % (e, x)
				total += 1

				base = x[:-3]

				print 'Running test', base, '...'
				if not runTest(base):
					if not options.continueAfterFailure:
						halt = True
					failed += 1

				if halt:
					break

			print '\n'
		else:
			print 'not a directory:', e

		if halt:
			break



	print 'total:', total
	print 'failed:', failed
	print 'succeeded:', total - failed
	if halt:
		print 'errors occured, stopped early'

	if failed:
		return 1
	else:
		return 0



if __name__ == '__main__':
	sys.exit(main())


