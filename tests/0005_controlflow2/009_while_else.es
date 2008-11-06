

def main() as int32
{
	x = 0;
	i = 5;
	while i > 100
	{
		i += 1;
	}
	else
	{
		x = 42;
	}
	assert i == 5;
	assert x == 42;


	return 0;
}


