module t002

def main() as int32
{
	a = 8h;// int16
	assert a + 32760h == -32768h;

	b = 8hh;// int8
	assert b + 120hh == -128hh;

	assert -128hh - 1hh == 127hh;

	assert 0hh + (- 32768h) == -32768; // FIXME? without parenthesis this is parsed as 0hh - (32768h); and 32768h is not a valid int16!


	return 0;
}

