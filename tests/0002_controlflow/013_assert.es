
def main() as int32
{
	assert not 42;# this will cause an abort --> SIGABRT --> exit code 134

	return 42;
}

