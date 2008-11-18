module t0010

alias int as int32


def main() as int32
{
	x = 42;

	y = cast(21 as int);
	x -= y;
	assert x == 21;

	alias short as int16;
	z as short;
	z = 21;
	z += 21h;
	assert z == 42;


	alias pint32 as int32*;
	
	p1 as int32*;
	p2 as pint32;
	p2 = p1;

	return 0;
}

