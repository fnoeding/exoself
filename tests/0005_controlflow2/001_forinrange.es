
def main() as int32
{
	x = 1;
	for i in range(1 /* start */, 7 /* end, exclusive */, 1 /* step */)
	{
		x *= i;
	}
	assert x == 720;

	x = 1;
	for i in range(5) # == range(0, 6, 1)
	{
		x *= i + 1;
	}
	assert x == 120;

	x = 0;
	for i in range(4, 10, 3)
	{
		x += i;
	}
	assert x == 11;

	x = 0;
	for i in range(5, 9)
	{
		x += i;
	}
	assert x == 26;

	return 0;
}

