module t004
def f() as int32
{
	return 42;
}

def main() as int32
{
	x as int32;
   	x = f();


	return x - 42;
}

