
def f(x as int32) as int32
{
	x = x * x;
	x = x + 7;

	return x - 3;
}


def main() as int32
{
	assert f(5) == 29;
	assert f(-3) == 13;

	return 0;
}
