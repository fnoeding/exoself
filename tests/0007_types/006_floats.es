module t006

def main() as int32
{
	x as float64;
	x = 5 ** 4;
	assert x == 625;

	x **= 2;
	assert x == 625 * 625;


	return 0;
}


