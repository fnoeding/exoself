module t004


def main() as int32
{
	i = 42;
	x = 0;
	for i in range(50)
	{
		x += i;
		if i == 10
		{
			break;
		}
	}
	assert i == 10;
	assert x == 55;


	return 0;
}

