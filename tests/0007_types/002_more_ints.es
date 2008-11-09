module t002


def main() as int32
{
	a as int8;
	b as int8;

	a = 120;
	b = 8;

	c = a + b;
	assert c == -128;

	d as int32;
	d = c;
	assert d == -128;


	return 0;
}

