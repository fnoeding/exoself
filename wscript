#!/usr/bin/python

import os

srcdir = 'src'
blddir = 'build'

dirs = 'compiler runtime hacks tests'.split()





def set_options(opt):
	for d in dirs:
		opt.sub_options('src/' + d)


	# provide options of used modules
	opt.tool_options('gcc')
	opt.tool_options('g++')



def configure(conf):
	root, ign = os.path.split(conf.srcdir)

	# get gcc / g++
	conf.check_tool('gcc')
	conf.check_tool('g++')

	# exoself
	conf.check_tool('exoself', tooldir='./waftools')



	for d in dirs:
		conf.sub_config('src/' + d)

	conf.env['CFLAGS'] = '-g -Wall'
	conf.env['CXXFLAGS'] = '-g -Wall'

	# setup 3rdparty tools
	oldCwd = os.path.abspath(os.getcwd())
	os.chdir(os.path.join(root, '3rdparty'))
	os.system('./setup.sh')
	os.chdir(oldCwd)
	




def build(bld):
	for d in dirs:
		bld.add_subdirs(d)


def shutdown():
	from waftools import myunittest
	ut = myunittest.my_unit_test()
	ut.change_to_testfile_dir = True
	ut.run()
	ut.print_results()
