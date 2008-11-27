module t011

typedef B as int32

def main() as int32
{
	b as B;
	b = cast(5 as B); // b = 5 must not work!

	return 0;
}
