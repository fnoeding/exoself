module t019;


// dlXXX functions
typedef dlhandle as void*;
def(mangling=C) dlopen(filename as byte*, flag as int32) as dlhandle;
def(mangling=C) dlsym(handle as dlhandle, symbol as byte*) as void*;
def(mangling=C) dlclose(handle as dlhandle) as int32;

// malloc, free handles
alias FTmalloc as function(word) as void*;
alias FTfree as function(void*) as void;

def main() as int32
{
	RTLD_DEFAULT = cast(None as dlhandle);// cast(0 as void*); opening the (wrong) libc.so using dlopen will result in "interesting" failures...

	dlsym_by_ptr = dlsym;// a function name is equal to the address of the function

	libc_malloc = cast(dlsym_by_ptr(RTLD_DEFAULT, ar"malloc") as FTmalloc);
	libc_free = cast(dlsym_by_ptr(RTLD_DEFAULT, ar"free") as FTfree);

	data as void*;
	data = None;
	data = libc_malloc(1024u * 1024u * 25u);
	assert data != None;

	ui32P = cast(data as uint32*);
	for i in range(1024 * 1024 * 24 / 4)
	{
		ui32P[i] = 0xDEADBEAFu;
	}

	libc_free(ui32P);


	return 0;
}

