module t015;


struct S
{
	x as int32;
}


def main() as int32
{
	s as S;

	s.x = 21;

	return 42 - 2 * s.x;
}
