

def ntohl(x as int32) as int32;
def htonl(x as int32) as int32;


def main() as int32
{
	return htonl(ntohl(42));
}

