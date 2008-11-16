module t009


def main() as int32
{
	x = 0;
	x += 1;
	assert x == 1;

	x = 5;
	x += x * 3;
	assert x == 20;

	x -= 3 * 3;
	assert x == 11;




	return 0;
}

