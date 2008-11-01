
def main() as int32
{
	assert not 42;# this fill cause a trap --> SIGILL --> exit code 132

	return 42;
}

