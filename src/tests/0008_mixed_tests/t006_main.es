
from .t006_mod import *;


def main() as void
{
	assert answer == 42;
	assert get() == 42;

	set(21);
	assert answer == 21;
	assert get() == 21;
}
