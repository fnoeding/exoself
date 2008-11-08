module t003

def main() as int32
{
	a = 0;
	b = 1;

	for i in range(45)
	{
		a, b = b, b + a;
	}
	assert b == 1836311903;


	return 0;
}

