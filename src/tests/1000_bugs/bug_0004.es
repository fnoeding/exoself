

a as A;// reference to A which is only later defined
b as B;


def x() as A;
def y() as B;


typedef A as int32;
alias B as int32;


// function prototypes are processed before other things
def f() as A;
def g() as B;



def main() as void
{
	a = cast(0 as A);
	b = 0;
}

