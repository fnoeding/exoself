
from .formatting import *
from .test2 import *

def(mangling=C) puts(s as byte*) as int32;



def main() as int32
{
	puts(ar"hello???");

	if f() == 42
	{
		puts(ar"answer was correct!");
	}

	p = new(byte, 1024);
	formatInt32(p, 1024u, ar"%d", f());
	puts(p);

	format(p, 1024ul, ar"now using format instead of formatInt32: %d", f());
	puts(p);

	return 0;
}
