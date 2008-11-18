module t0017

typedef X as int32

def main() as int32
{
	x as X;
	x = 42; // must fail, no implicit conversion!


	return 0;
}
