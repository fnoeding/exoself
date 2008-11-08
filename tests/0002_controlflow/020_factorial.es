module t020

def fac(n as int32) as int32
{
	if n < 2
	{
		return 1;
	}
	
	return n * fac(n - 1);
}


def main() as int32
{
	assert fac(0) == 1;
	assert fac(1) == 1;
	assert fac(2) == 2;
	assert fac(3) == 6;
	assert fac(4) == 24;
	assert fac(5) == 120;
	assert fac(6) == 720;
	assert fac(12) == 479001600;

	return 0;
}
