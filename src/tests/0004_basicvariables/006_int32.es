module t006
def f() as int32
{
	return 7;
}

def main() as int32
{
	x = y = f();

	assert x == f();
	assert y == f();

	return 0;
}
