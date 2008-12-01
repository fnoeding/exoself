module t003;


struct S
{
	a, b, c as int32;
}


def main() as void
{
	x, y, z as int32;
	assert x == 0;
	assert y == 0;
	assert z == 0;

	s as S;
	assert s.a == 0;
	assert s.b == 0;
	assert s.c == 0;

}
