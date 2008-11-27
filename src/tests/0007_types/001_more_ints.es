module t001


def main() as int32
{
	a8 as int8;
	a8 = 21;
	assert a8 == 21;

	b8 as int8;
	b8 = 2;
	assert b8 == 2;

	c8 = a8 * b8;
	assert c8 == 42;


	a64 as int64;
	a64 = 2_000_000_000;
	assert a64 == 2_000_000_000;
	b64 as int64;
	b64 = 10;
	assert b64 == 10;
	assert (a64 * b64) == 20_000_000_000;


	return 0;
}

