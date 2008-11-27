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



def c() as float64
{
	return 0.5;
}


def f() as void
{
	x = cast(malloc(2 * 8) as float64*);


	a = 0.5;

	x[0] = -a / c();


	free(x);
}



def main() as int32
{
	myFree(myAlloc(1024 * 1024));




	return 0;
}

