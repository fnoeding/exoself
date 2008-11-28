module t016;


struct S
{
	x as int32;
	y as float64;
}


def f() as S
{
	s as S;
	s.x = 1;
	s.y = 2.0;

	return s;
}



def main() as int32
{
	s as S;
	s.x = 42;
	s.y = 0.5;

	assert s.x == 42;
	assert s.y == 0.5;
	assert s.x * s.y == 21.0;

	s = f();
	assert s.x == 1;
	assert s.y == 2.0;


	p as S*;
	p = new(S, 100);
	for i in range(100)
	{
		p[i].x = i;
		(*(&(p[i]))).y = i * i;
	}

	for i in range(99, -1, -1)
	{
		assert p[i].y == i * i;
		p2 as S*;
		p2 = &(p[i]);
		assert (*p2).x == i;
	}
	

	return 0;
}



