module t005

def main() as int32
{
	x = 42;

	a as int8;
	a = cast(x as int8);
	assert a == 42;

	a = cast(21 as int8);
	assert a == 21;

	a = 2hh * cast(42 as int8) + 7hh;
	assert a == 91;

	d as int64;
	d = cast(2 ** 40 as int64);// while writing this test case 2 ** 40 generates a float64, even when both operands are integers


	return 0;
}

