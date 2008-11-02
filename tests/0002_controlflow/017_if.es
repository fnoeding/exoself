
def main() as int32
{
	if 1
	{
		if 0 {return 0;}
		else if 1
		{
			if 1 {return 1;}
			else {return 4;}
		}
		else {return 2;}

		# we can not get here!
	}
	else {return 3;}

	# we can not get here!
}
