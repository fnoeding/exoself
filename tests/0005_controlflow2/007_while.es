




def main() as int32
{
	i = 0;
	x = 0;
	while i < 100
	{
		x += i;
		i += 1;
	}
	assert i == 100;
	assert x == 4950;

	return 0;
}
