module t018;


def f() as int32
{
	return 0;
}

def f(x as int32) as int32
{
	return 1;
}

def f(x as float32) as int32
{
	return 2;
}

def f(x as int64) as int32
{
	return 3;
}


def f(x as uint32) as int32
{
	return 4;
}

def f(x as float64) as int32
{
	return 5;
}

def f(x as uint64) as int32
{
	return 6;
}


def f(x as int16) as int32
{
	return 7;
}



def main() as void
{
	assert f() == 0;
	assert f(10) == 1; // 10 is a int32 constant
	assert f(2.0f) == 2; // 2.0f is a float32
	assert f(1l) == 3;
	assert f(1u) == 4;
	assert f(1.0) == 5;
	assert f(1ul) == 6;
	assert f(1h) == 7;
}
