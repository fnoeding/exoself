module t005;

// default initialized globals
answer as int32;
pi as float64;


def ctor() as void // ctor is a special function name; this function is a module constructor and is called before main is entered
{
	answer = 42;
	pi = 3.1415926535897931;
}



def dtor() as void // same as ctor, but dtor is called after main is left
{
	assert answer == 21;
}





def main() as void
{
	assert answer == 42;
	answer = 21;
	assert pi > 3.1315 and pi < 3.1416;
}

