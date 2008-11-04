

def main() as int32
{
	x = 32;

	{
		y = 43;
		x = 42;
	}
	assert x == 42;

	{
		y = 5;
		assert y == 5;
	}

	return 0;
}

