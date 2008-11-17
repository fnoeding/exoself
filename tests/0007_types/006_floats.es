module t006

def main() as int32
{
	x as float64;
	x = 5 ** 4;
	assert x == 625;

	x **= 2;
	assert x == 625 * 625;

	assert 2 * .5 == 1;
	assert 2 + 5.0 / 2 == 4.5;
	assert 2 - 5.0 / 2 == -0.5;

	assert 0.5 * 2 == 1;
	assert 3 / 2 == 1;

	assert 5.0;
	assert not 0.0;


	return 0;
}


