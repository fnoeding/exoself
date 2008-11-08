module t006

def main() as int32
{
	x = 0;
	for i in range(1000)
	{
		if i > 550 and i < 560
		{
			continue;
		}

		for j in range(1000)
		{
			if i + j > 500
			{
				break;
			}
			if j > 950
			{
				continue;
			}

			x += j;
		}

		if i > 990
		{
			break;
		}
	}

	assert x == 20958500;

	return 0;
}

