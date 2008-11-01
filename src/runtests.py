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

options = None
args = None


def runExoself(filebase, opts):
	exitStatus = os.system('../src/exoself --save-temps %s %s.es' % (opts, filebase))
	if os.WEXITSTATUS(exitStatus) != 0:
		print 'compilation failed'
		return False

	return True



def runTest(filebase):
	path, filename = os.path.split(filebase)

	if not runExoself(filebase, '-A'): # only ast
		return False

	# verify ast
	if os.path.exists('%s.ast' % filebase):
		expectedAST = file('%s.ast' % filebase).read()
		expectedAST = ' '.join(expectedAST.split()).strip()

		astString = file('../tests_tmp/%s.ast' % filename).read().strip()
		if astString != expectedAST:
			print 'received ast: %s\nexpected ast: %s' % (astString, expectedAST)
			return False

	if not runExoself(filebase, '-c'): # generate bitcode
		return False

	# run code, check return value
	if os.path.exists('%s.ret' % filebase):
		expectedRetval = file('%s.ret' % filebase).read().strip()
		expectedRetval = int(expectedRetval) & 0xFF

		if expectedRetval < 0:
			expectedRetval = 256 - abs(expectedRetval)


		exitStatus = os.system('%s ../tests_tmp/%s.bc' % (options.lli, filename))
		retVal = os.WEXITSTATUS(exitStatus)
		if retVal != expectedRetval:
			print 'received ret: %d\nexpected ret: %s' % (retVal, expectedRetval)
			return False


	return True


def main():
	global options
	global args

	parser = OptionParser()
	parser.add_option('-s', '--suite', help='test suite prefix', dest='suitePrefix', default='')
	parser.add_option('-k', '--continue', help='continue even when tests fail', dest='continueAfterFailure', action='store_true', default=False)
	parser.add_option('--lli', help='path to lli command', dest='lli', default='~/llvm/bin/lli')

	options, args = parser.parse_args()

	# switch to temp dir, cleanup
	# several temporary files will be generated here
	os.chdir('../tests_tmp')
	os.system('rm -f *.ast *.ll *.bc')

	total = 0
	failed = 0

	halt = False

	l = os.listdir('../tests')
	l.sort()
	for e in l:
		if options.suitePrefix and not e.startswith(options.suitePrefix):
			continue

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


