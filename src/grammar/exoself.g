/*
The BSD License

Copyright (c) 2008, Florian Noeding
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.
Neither the name of the of the author nor the names of its contributors may be
used to endorse or promote products derived from this software without specific
prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

grammar exoself;

options {
	output = AST;
	language = Python;
}

tokens {
	PASS;
	RETURN;

	MODULE;
	DEFFUNC;
	DEFFUNCARGS;
	DEFVAR;
	BLOCK;
	SIMPLE_STATEMENT;
	INTEGER_CONSTANT;
	FLOAT_CONSTANT;
	VARIABLE;
	CALLFUNC;
}


// keywords
DEF: 'def';
AS: 'as';
PASS: 'pass';// in principle not needed, since we are using no significant whitespace. But reserve it for later extension in that direction
RETURN: 'return';
ASSERT: 'assert';
OR: 'or';
XOR: 'xor';
AND: 'and';
NOT: 'not';

fragment LowercaseLetter: 'a' .. 'z';
fragment UppercaseLetter: 'A' .. 'Z';
fragment Letter: LowercaseLetter | UppercaseLetter;

fragment Digit: '0' .. '9';
fragment SpacedDigit: Digit ((Digit | '_')* Digit)?;
fragment HexDigit: Digit | 'a' .. 'f' | 'A' .. 'F';
fragment SpacedHexDigit: HexDigit ((HexDigit | '_')* HexDigit)?;
fragment BinaryDigit: '0' | '1';
fragment SpacedBinaryDigit: BinaryDigit ((BinaryDigit | '_')* BinaryDigit)?;
fragment Float: Digit* '.' Digit+ (('e' | 'E') ('+' | '-')? Digit+)?;


INTEGER: SpacedDigit | ('0x' | '0X') SpacedHexDigit | ('0b' | '0B') SpacedBinaryDigit;// octal integers are also matched by SpacedDigit
FLOAT: Float;// TODO HexFloat for exact representation
NAME: (Letter | '_') (Letter | Digit | '_')*;





COMMENT: '#' (~('\n' | '\r'))* ('\n' | '\r' ('\n')?) {$channel=HIDDEN};
MULTILINE_COMMENT: '/*' (options {greedy=false;}: ~('*/'))* '*/' {$channel=HIDDEN};

NEWLINE: (('\r')? '\n')+ {$channel=HIDDEN};
WS: (' ' | '\t')+ {$channel=HIDDEN;};




SEMI: ';';
PLUS: '+';
MINUS: '-';
ASTERISK: '*';
PERCENT: '%';
SLASH: '/';
DOUBLESLASH: '//';
COLON:	':';
LPAREN: '(';
RPAREN: ')';
LCURLY: '{';
RCURLY: '}';
LBRACKET: '[';
RBRACKET: ']';
ASSIGN: '=';
COMMA: ',';
LESS: '<';
LESSEQUAL: '<=';
EQUAL: '==';
NOTEQUAL: '!=';
GREATEREQUAL: '>=';
GREATER: '>';

start_module: global_stmt* EOF-> ^(MODULE global_stmt*);

global_stmt: deffunc;

simple_stmt: pass_stmt | return_stmt | expr | defvar | assign_stmt | assert_stmt;

assign_stmt: simple_assign;
simple_assign: NAME ASSIGN expr -> ^(ASSIGN NAME expr);


pass_stmt: PASS^;
return_stmt: RETURN^ expr?;
assert_stmt: ASSERT^ expr;


defvar: n=NAME AS t=NAME -> ^(DEFVAR $n $t);

deffunc: DEF NAME LPAREN deffuncargs RPAREN AS NAME (block | SEMI) -> ^(DEFFUNC NAME NAME deffuncargs block?);
deffuncargs: (NAME AS NAME COMMA)* (NAME AS NAME)? -> ^(DEFFUNCARGS NAME*);

block: LCURLY
			(simple_stmt SEMI+)*
		RCURLY -> ^(BLOCK simple_stmt*);


test_expr: or_test;
or_test: xor_test (OR^ xor_test)*;
xor_test: and_test (XOR^ and_test)*;
and_test: not_test (AND^ not_test)*;
not_test: NOT^ not_test | comparison;

comparison: arith_expr (comp_op^ arith_expr)*;
comp_op: LESS | LESSEQUAL | EQUAL | NOTEQUAL | GREATEREQUAL | GREATER;

expr: test_expr;// was: arith_expr
arith_expr: term ((PLUS^ | MINUS^) term)*;
term: factor ((ASTERISK^ | SLASH^ | DOUBLESLASH^ | PERCENT^) factor)*;
factor:
	PLUS^ factor
	| MINUS^ factor
	| power;
power: atom;
atom: LPAREN expr RPAREN -> expr
	| integer_constant
	| float_constant
	| variable_name
	| function_call;

integer_constant:
	INTEGER -> ^(INTEGER_CONSTANT INTEGER);

float_constant:
	FLOAT -> ^(FLOAT_CONSTANT FLOAT);

variable_name: NAME -> ^(VARIABLE NAME);

function_call: NAME LPAREN (expr (COMMA expr)* COMMA?)? RPAREN -> ^(CALLFUNC NAME expr*);


