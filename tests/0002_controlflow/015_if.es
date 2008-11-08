module t015

def main() as int32
{
	if 0 + 0
	{
		assert 0;
	}

	if 5 % 3 != 2 {assert 0;}

	if 1 {}
	else {assert 0;}

	if 5 == 2 {assert 0;}
	else if 3 < -3 {assert 0;}
	else if 5 * 2 == 7 {assert 0;}
	else if 9 == 89 / 3 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else if 0 {assert 0;}
	else {}

	if 5 == 2 + 3 {}
	else if 3 == 3 {assert 0;}

	if 3 == 5 {assert 0;}
	else if 42 == 42 {}
	else if 3 == 5 {assert 0;}
	else {assert 0;}

	if 1 and 0 {assert 0;}
	else if 0 xor 1
	{
		if 9 {}
		else {assert 0;}
	}
	else {assert 0;}


	return 0;
}

