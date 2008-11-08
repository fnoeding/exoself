module t001

def avg(a as int32, b as int32) as int32
{
	return (a + b) // 2;
}


def reversedDiff(a as int32, b as int32) as int32
{
	return b - a;
}


def main() as int32
{
	assert 4 avg 8 == 6;
	assert 4 + 10 avg 2 == 10;
	assert 5 reversedDiff 10 == 5;
	assert 3 reversedDiff 5 avg 4 == 3;
	assert (2 + 2) reversedDiff 10 == 6;

	return 0;
}
