module t001main

# use explicit declaration

def(mangling=C) f() as int32;# defaults to extern

def main() as int32
{
	return f() - 42;
}

