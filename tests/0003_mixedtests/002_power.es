

def main() as int32
{
	assert 0 ** 0 == 1;
	assert 1 ** 100 == 1;
	assert 2 ** 3 == 8;
	assert 3 ** 4 == 81;
	assert 4 ** 5 == 1024;
	assert 3 + 4 ** 5 + 7 == 1034;
	assert 2 ** 3 ** 2 == 512;

	return 0;
}

