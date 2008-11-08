module t007
def f(x as int32, y as int32) as int32
{
	x = y + 2;
	y = 3 * x + y;

	return x + y;
}

def g(x as int32) as int32
{
	return 42 * x;
}


def main() as int32
{
	assert 1 f 2 == 18;
	x = 1 f 2 + g(0);
	assert x == 18;

	a = x = c = 42;
	assert a == 42;
	assert x == 42;
	assert c == 42;

	return 0;
}

