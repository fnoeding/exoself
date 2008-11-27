#!/usr/bin/python


from TaskGen import *
import Utils


def detect(conf):
	import os


	conf.env['EXOSELF'] = os.path.join(conf.srcdir, 'compiler', 'exoself')


	conf.env['LLVM_LINK'] = conf.find_program('llvm-link')
	conf.env['LLVM_LLC'] = conf.find_program('llc')
	conf.env['LLVM_NATIVE_C'] = conf.find_program('gcc')




Task.simple_task_type('exoself', '${EXOSELF} -c -o ${TGT} ${SRC}', color='BLUE')
Task.simple_task_type('llvm-link', '${LLVM_LINK} -f -o ${TGT} ${SRC}')
Task.simple_task_type('llvm-llc', '${LLVM_LLC} -f -o ${TGT} ${SRC}')
Task.simple_task_type('llvm-native-compile', '${LLVM_NATIVE_C} -c -o ${TGT} ${SRC}')



class es_taskgen(task_gen):
	def __init__(self, *k, **kw):
		task_gen.__init__(self, *k, **kw)



@taskgen
@feature('es')
def init_es(self):
	# TODO check source, target, ...
	self.features = ['program'] # FIXME




@taskgen
@after('init_es')
@feature('es')
def apply_source(self):
	self.llvmObjects = []

	searchDirs = [self.path]
	searchDirs.extend(self.path.dirs())

	# compile .es to .bc
	compileTasks = []
	for filename in self.source.split():
		inNode = None
		for sd in searchDirs:
			inNode = sd.find_resource(filename)
			if inNode:
				break

		if not inNode:
			raise Utils.WafError("file '%s' was not found (required by '%s')" % (filename, self.name))


		outNode = inNode.change_ext('.bc')

		t = self.create_task('exoself')
		t.set_inputs(inNode)
		t.set_outputs(outNode)
		compileTasks.append(t)

		self.llvmObjects.append(outNode)

		# force rebuild when compiler was changed
		# everything depending on this file will also need an update!
		self.bld.add_manual_dependency(outNode, self.bld.ESCompilerHash)


	# TODO call opt

	# combine .bc to target
	if len(self.llvmObjects) > 1:
		linkTask = self.create_task('llvm-link')
		linkTask.set_inputs(self.llvmObjects)
		targetNode = self.path.find_or_declare(self.llvmTarget)
		linkTask.set_outputs(targetNode)
		for x in compileTasks:
			linkTask.set_run_after(x)

		self.llvmCombinedObject = targetNode
	else:
		self.llvmCombinedObject = self.llvmObjects[0] # FIXME ignores llvmTarget
		linkTask = compileTasks[0]


	# compile to native
	target = getattr(self, 'target', None)
	if target:

		# compile .bc to .s
		compileTask = self.create_task('llvm-llc')
		compileTask.set_inputs(self.llvmCombinedObject)
		targetNode = self.path.find_or_declare(self.target).change_ext('.s')
		compileTask.set_outputs(targetNode)
		compileTask.set_run_after(linkTask)

		self.nativeAssembly = targetNode


		# compile .s to .o
		nativeCompileTask = self.create_task('llvm-native-compile')
		nativeCompileTask.set_inputs(self.nativeAssembly)
		targetNode = self.path.find_or_declare(self.target).change_ext('.o')
		nativeCompileTask.set_outputs(targetNode)
		nativeCompileTask.set_run_after(compileTask)

		self.nativeObject = targetNode


		# link
		libPaths = []

		linkWith = []
		if hasattr(self, 'uselib'):
			l = self.uselib.split()
			linkWith.extend(l)

		linkWithLocal = []
		if hasattr(self, 'uselib_local'):
			localPackages = Utils.to_list(self.uselib_local)
			seen = []
			while len(localPackages) > 0:
				package = localPackages.pop()
				if package in seen:
					continue
				seen.append(package)

				# check if package exists
				packageObj = self.name_to_obj(package)
				if not packageObj:
					raise Utils.WafError("object '%s' was not found in uselib_local (required by '%s')" % (package, self.name))

				packageName = packageObj.target
				packageNode = packageObj.path
				packageDir = packageNode.relpath_gen(self.path)

				
				for task in packageObj.tasks:
					found = False
					for output in task.outputs:
						if output.name == 'lib%s.so' % packageName: # FIXME
							found = True
							
							p, ign = os.path.split(output.bldpath(self.env))
							if not p in libPaths:
								libPaths.append(p)
							break
					if found:
						linkWithLocal.append(packageObj.target)
						nativeCompileTask.set_run_after(task) # could also be nativeLinkTask but the linking has to wait for compilation


		if linkWithLocal or linkWith:
			for x in libPaths:
				self.env.append_unique('LINKFLAGS', self.env['LIBPATH_ST'] % x)
				self.env.append_unique('LINKFLAGS', self.env['STATICLIBPATH_ST'] % x)

			self.env.append_value('LINKFLAGS', self.env['SHLIB_MARKER'])
			for x in linkWithLocal:
				s = self.env['LIB_ST'] % x
				self.env.append_unique('LINKFLAGS', s)
			for x in linkWith:
				s = self.env['LIB_ST'] % x
				self.env.append_unique('LINKFLAGS', s)
			#print '==============================================='
			#print self.env['LINKFLAGS']
			#print '==============================================='


		nativeLinkTask = self.create_task('cc_link')
		nativeLinkTask.set_inputs(self.nativeObject)
		targetNode = self.path.find_or_declare(self.target)
		nativeLinkTask.set_outputs(targetNode)
		nativeLinkTask.set_run_after(nativeCompileTask)

		self.nativeProgram = targetNode
	




