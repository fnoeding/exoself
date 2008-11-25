module t014

def main() as int32
{

	p = new(int32);
	p100 = new(int32, 100);

	for i in range(100)
	{
		p100[i] = i * i;
	}
	
	*p = 0;
	for i in range(100)
	{
		*p = (*p) + p100[i];
	}
	assert *p == 328350;

	return 0;
}

