def f(a as int32) as int32
{
	return a * a - 3 * a + 11;
}

def avg(a as int32, b as int32, c as int32) as int32
{
	return (a + b + c) / 3;
}


def main() as int32
{
	return f(2) * avg(4, 2, 3);
}
