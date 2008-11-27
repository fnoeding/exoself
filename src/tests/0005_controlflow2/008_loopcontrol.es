module t008


def main() as int32
{
	i = 0;
	
	x = 0;
	while i < 10
	{
		if i > 8
		{
			i += 1;
			continue;
		}

		j = 0;
		while j < 50
		{
			if j == 45
			{
				break;
			}

			x += i + j;
			j += 1;
		}
		assert j == 45;

		for j in range(10)
		{
			x += j;
		}

		i += 1;
	}

	assert i ==10;
	assert x == 10935;

	return 0;
}

