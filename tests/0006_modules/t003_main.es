module t003

def f() as int32
{
	return 42;
}


def f(x as int32) as int32
{
	return 2 * x;
}


def main() as int32
{
	return f() - f(21);
}

