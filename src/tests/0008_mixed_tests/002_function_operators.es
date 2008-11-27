module t002



def div(l as float64, r as float64) as float64
{
	return l / r;
}


def add(l as float64, r as float64) as float64
{
	return l + r;
}


def mul(l as float64, r as float64) as float64
{
	return l * r;
}


def sub(l as float64, r as float64) as float64
{
	return l - r;
}


def main() as int32
{
	x = 2.0 div 4;
	assert x == 0.5;

	y = 2.0 div 4 div 0.25;
	assert y == 2.0;

	assert 9.0 sub 3.0 div 0.5 mul 4.0 == 48.0;


	return 0;
}

