module t013

def(mangling=C) puts(_ as byte*) as int32;


def main() as int32
{
	s as byte*;
	s = ar"Much simpler hello world!";

	puts(s);

	puts(ar"Hallo Welt!");

	return 0;
}

