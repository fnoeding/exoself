

def main() as int32
{
	x = 42;
	y = 21;

	x, y = y, x;

	assert x == 21;
	assert y == 42;


	a,b = x,y;
	assert a == x;
	assert b == y;

	oldY = y;
	y,b,b,c = a,y,y,y;
	assert y == a;
	assert b == oldY;
	assert c == oldY;

	return 0;
}

