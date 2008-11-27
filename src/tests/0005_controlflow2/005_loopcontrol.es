module t005

def main() as int32
{
	x = 1;
	i = 42;
	for i in range(50)
	{
		if i < 1 or i > 13
		{
			continue;
		}

		x *= i;
	}

	assert x == 479001600 * 13;
	assert i == 50;

	return 0;
}

