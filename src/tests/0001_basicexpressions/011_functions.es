module t011


def(mangling=C) ntohl(x as int32) as int32;
def(mangling=C) htonl(x as int32) as int32;


def main() as int32
{
	return htonl(ntohl(42));
}

