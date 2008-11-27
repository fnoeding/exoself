


def main() as int32
{
	// we must not use tree.text / ast.text to get the node type during desugaring!
	// As long as we walk all nodes in a controlled fashion like in ASTWalker that's
	// not a problem. But when iterating over all nodes the text field can not be used
	// to get the type in a reliable way
	IMPORTALL as int32;

	return 0;
}

