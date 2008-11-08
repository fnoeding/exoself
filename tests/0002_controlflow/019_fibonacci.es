module t019


def fib(n as int32) as int32
{
	if n == 0 {return 0;}
	else if n == 1 {return 1;}

	return fib(n - 1) + fib(n - 2);
}


def main() as int32
{
	return fib(13);
}
