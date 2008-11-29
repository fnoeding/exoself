module t003


def f(x as int8) as int32
{
	a as int32;
	a = x;

	return 100 * a;
}


def g(x as int8) as int32
{
	return x + 10;# 10 is an int32 --> calculation is done using int32
}


def h(x as int8) as int8
{
	y as int8;
	y = 1;
	return x + y; # x + y is int8 --> calculation is done as int8, and then promoted to int32
}


def main() as int32
{
	assert g(118hh) == 128;
	assert h(126hh) == 127;
	assert h(127hh) == -128;

	return f(5hh) - 500;
}

