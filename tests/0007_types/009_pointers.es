module t009


def(mangling=C) malloc(size as int64) as void*;
def(mangling=C) free(p as void*) as void;



def myAlloc(x as int64) as void*
{
	return malloc(x);
}


def myFree(p as void*) as void
{
	free(p);
}



def main() as int32
{
	myFree(myAlloc(1024 * 1024));

	return 0;
}

