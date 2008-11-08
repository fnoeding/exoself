module t018

def ackermann(m as int32, n as int32) as int32
{
	if m == 0
	{
		return n + 1;
	}
	else if n == 0
	{
		return ackermann(m - 1, 1);
	}
	else
	{
		return ackermann(m - 1, ackermann(m, n - 1));
	}
}


def main() as int32
{
	assert ackermann(0, 0) == 1;
	assert ackermann(1, 0) == 2;
	assert ackermann(2, 0) == 3;
	assert ackermann(3, 0) == 5;

	assert ackermann(0, 1) == 2;
	assert ackermann(1, 1) == 3;
	assert ackermann(2, 1) == 5;
	assert ackermann(3, 1) == 13;

	assert ackermann(0, 2) == 3;
	assert ackermann(1, 2) == 4;
	assert ackermann(2, 2) == 7;
	assert ackermann(3, 2) == 29;

	assert ackermann(0, 3) == 4;
	assert ackermann(1, 3) == 5;
	assert ackermann(2, 3) == 9;
	assert ackermann(3, 3) == 61;

	return 0;
}

