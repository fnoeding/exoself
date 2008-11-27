module t014


def main() as int32
{
	assert 0 < 5;
	assert not 5 < 0;
	assert -5 < -4;
	assert -5 < 10;

	assert 0 <= 5;
	assert 0 <= 0;
	assert -3 <= 2;
	assert -4 <= -4;

	assert 42 == 2 * 21;
	assert not 42 == 21;

	assert 42 != 21;
	assert not 42 != 42;

	assert 7 >= 7;
	assert 7 >= 0;
	assert 9 >= -2;
	assert -3 >= -4;

	assert 13 > 0;
	assert not 13 > 13;
	assert -13 > -27;
	assert 9 > -7;

	return 0;
}
