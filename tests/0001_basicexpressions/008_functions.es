module t008


def f() as int32
{
	return 17;
}


def g() as int32
{
	return 14;
}


def main() as int32
{
	return f() - g();
}

