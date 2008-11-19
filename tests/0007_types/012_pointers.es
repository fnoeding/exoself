module t012

def(mangling=C) malloc(size as int64) as void*;
def(mangling=C) free(p as void*) as void;



def pointerPassThrough(p as int32*) as int32*
{
	return p;
}


def int32PassThrough(x as int32) as int32
{
	return x;
}


def main() as int32
{
	p = cast(malloc(1024 * 4) as int32*);
	p2 = cast(malloc(1024 * 4) as int32*);
	for i in range(1024)
	{
		p[i] = i;
		p2[i] = i * i;
	}

	assert p[42] == 42;
	assert p[2 * 21] == 42;

	p[2 + 3] = 0;
	assert 0 == p[5];

	*p = *p2 = 9;
	assert p[0] == 9;
	assert p2[0] == 9;

	assert p2[p[0]] == 81;

	assert pointerPassThrough(p)[0] == 9;
	assert *pointerPassThrough(p) == 9;


	*pointerPassThrough(p2) = 0;
	assert *pointerPassThrough(p2) == 0;
	assert pointerPassThrough(p2)[0] == 0;
	
	pointerPassThrough(p2)[0] = 1;
	assert *pointerPassThrough(p2) == 1;
	assert pointerPassThrough(p2)[0] == 1;

	assert int32PassThrough(pointerPassThrough(p2)[0]) == 1;
	assert int32PassThrough(*pointerPassThrough(p2)) == 1;
	

	free(p);
	free(p2);

	return 0;
}

