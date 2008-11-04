
def main() as int32
{
	x = 0;
	i as int32;
	for i in range(10, -1, -1)
	{
		x += i;
	}
	assert x == 55;
	assert i == -1;

	return 0;
}

