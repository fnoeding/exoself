module t007


def(mangling=C) malloc(size as int64) as void*;
def(mangling=C) free(p as void*) as void;


def main() as int32
{
	p as int32*;
	pp as int32**;
	ppp as int32***;
	pMANY as int32*********************************;

	x as int32;

	p = cast(malloc(4) as int32*);
	x = *p;
	*p = 42;
	assert *p == 42;
	x = *p;
	free(p);

	pf as float64*;
	pf = cast(malloc(8) as float64*);
	*pf = 42;
	assert 42 == *pf;
	free(pf);



	return x - 42;
}
