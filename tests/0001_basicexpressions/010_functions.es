
def f() as int32
{
	return 2 * g();
}

def g() as int32
{
	return 21;
}

def main() as int32
{
	return f();
}

