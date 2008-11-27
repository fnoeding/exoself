module t008


def(mangling=C) malloc(size as int64) as void*;
def(mangling=C) free(p as void*) as void;




def main() as int32
{
	p as int32*;
	p = cast(malloc(4 * 1024) as int32*);
	for i in range(1024)
	{
		p[i] = i * i + i;
	}

	
	for i in range(1024)
	{
		assert p[i] == i * i + i;
	}
	free(p);

	p2 as float64*;
	p2 = cast(malloc(8 * 100) as float64*);
	for i in range(100)
	{
		p2[i] = p[i] * 0.5;
		assert p2[i] == p[i] * 0.5;
	}
	free(p2);



	return 0;
}


