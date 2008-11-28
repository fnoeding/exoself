module t017;


struct LL
{
	next as LL*;
	data as int32;

	debugging as LL*;
	debugging2 as LL**;
}


def appendNode(head as LL*, data as int32) as void
{
	p = head;
	while (p[0].next != None) == True
	{
		p = p[0].next;
	}

	n = new(LL);
	n[0].next = None;
	n[0].data = data;

	p[0].next = n;
}


def getNodeAtIndex(head as LL*, idx as int32) as LL*
{
	i = 0;
	
	p = head;
	while (p != None and i < idx) != False
	{
		p = p[0].next;
		i += 1;
	}

	return p;
}


def main() as int32
{
	head as LL*;
	head = new(LL);
	head[0].next = None;
	head[0].data = 0;


	for i in range(1, 11)
	{
		appendNode(head, i * i);
	}

	assert getNodeAtIndex(head, 3)[0].data == 9;
	assert getNodeAtIndex(head, 0)[0].data == 0;
	assert (*getNodeAtIndex(head, 7)).data == 49;


	return 0;
}

