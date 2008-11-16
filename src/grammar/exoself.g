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

//****************************************************************************
// Lexer
//****************************************************************************


tokens {
	MODULESTART;
	DEFFUNC;
	DEFFUNCARGS;
	DEFFUNCMODIFIERS;
	DEFVAR;
	BLOCK;
	SIMPLE_STATEMENT;
	INTEGER_CONSTANT;
	FLOAT_CONSTANT;
	VARIABLE;
	CALLFUNC;
	ASSIGNLIST;
	LISTASSIGN;
	FOREXPRESSION;
	IMPORTALL;
	CAST;// for now only used inside the compiler
}


// keywords
PACKAGE: 'package';
MODULE: 'module';
DEF: 'def';
AS: 'as';
PASS: 'pass';// in principle not needed, since we are using no significant whitespace. But reserve it for later extension in that direction
RETURN: 'return';
ASSERT: 'assert';
IF: 'if';
ELSE: 'else';
ELIF: 'elif';
FOR: 'for';
IN: 'in';
RANGE: 'range';
BREAK: 'break';
CONTINUE: 'continue';
WHILE: 'while';
IMPORT: 'import';
FROM: 'from';
OR: 'or';
XOR: 'xor';
AND: 'and';
NOT: 'not';


// literals
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

fragment IntegerSuffix:
		('u')? // unsigned
		(
			'hh' // int8
			| 'h' // int16
			// int32 has no suffix
			| 'l' // int64
		);

INTEGER: (SpacedDigit | ('0x' | '0X') SpacedHexDigit | ('0b' | '0B') SpacedBinaryDigit) IntegerSuffix?;// octal integers are also matched by SpacedDigit
FLOAT: Float;// TODO HexFloat for exact representation
NAME: (Letter | '_') (Letter | Digit | '_')*;

// whitespace, comments
COMMENT: ('#' | '//') (~('\n' | '\r'))* ('\n' | '\r' ('\n')?) {$channel=HIDDEN};
MULTILINE_COMMENT: '/*' (options {greedy=false;}: ~('*/'))* '*/' {$channel=HIDDEN};

NEWLINE: (('\r')? '\n')+ {$channel=HIDDEN};
WS: (' ' | '\t')+ {$channel=HIDDEN;};



// operators
SEMI: ';';
PLUS: '+';
MINUS: '-';
STAR: '*';
DOUBLESTAR: '**';
PERCENT: '%';
SLASH: '/';
COLON:	':';
LPAREN: '(';
RPAREN: ')';
LCURLY: '{';
RCURLY: '}';
LBRACKET: '[';
RBRACKET: ']';
ASSIGN: '=';
COMMA: ',';
DOT: '.';
LESS: '<';
LESSEQUAL: '<=';
EQUAL: '==';
NOTEQUAL: '!=';
GREATEREQUAL: '>=';
GREATER: '>';


//***************************************************************************
// Parser
//***************************************************************************


start_module: package_stmt? module_stmt? global_stmt* EOF-> ^(MODULESTART package_stmt? module_stmt? global_stmt*);


package_stmt: PACKAGE^ package_name;
package_name: NAME (DOT NAME)*;
module_stmt: MODULE^ NAME;


global_stmt: deffunc | import_stmt;

import_stmt:
	FROM module_name IMPORT STAR -> ^(IMPORTALL module_name);
module_name: DOT* NAME (DOT NAME)*;


compound_stmt: simple_stmt | if_stmt | for_stmt | while_stmt;

if_stmt: IF^ expr block (ELSE! IF! expr block)* (ELSE! block)?;

for_stmt: FOR^ NAME IN! for_expression block;
for_expression: RANGE^ LPAREN! expr (COMMA! expr (COMMA! expr)?)? RPAREN!;

while_stmt: WHILE^ expr block (ELSE! block)?;


simple_stmt: (pass_stmt | return_stmt | expr | defvar | assign_stmt | assert_stmt | break_stmt | continue_stmt) (SEMI!+);

assign_stmt: simple_assign | list_assign | aug_assign;
simple_assign: (NAME ASSIGN)+ expr -> ^(ASSIGN NAME* expr);
list_assign: list_assign_lhs ASSIGN list_assign_rhs -> ^(LISTASSIGN list_assign_lhs list_assign_rhs);
list_assign_lhs: NAME (COMMA NAME)+ -> ^(ASSIGNLIST NAME+);
list_assign_rhs: expr (COMMA expr)+ -> ^(ASSIGNLIST expr+);
aug_assign:
	NAME (
		op=PLUS
		| op=MINUS
		| op=STAR
		| op=SLASH
		| op=DOUBLESTAR
		| op=PERCENT
	) ASSIGN expr -> ^(ASSIGN NAME ^($op ^(VARIABLE NAME) expr));


pass_stmt: PASS^;
return_stmt: RETURN^ expr?;
assert_stmt: ASSERT^ expr;
break_stmt: BREAK^;
continue_stmt: CONTINUE^;


defvar: n=NAME AS t=NAME -> ^(DEFVAR $n $t);

deffunc:
	DEF deffuncmodifiers
	NAME
	deffuncargs AS NAME
	(block | SEMI)
	-> ^(DEFFUNC deffuncmodifiers NAME NAME deffuncargs block?);
deffuncargs: LPAREN (NAME AS NAME COMMA)* (NAME AS NAME)? RPAREN-> ^(DEFFUNCARGS NAME*);
deffuncmodifiers: (LPAREN NAME ASSIGN NAME (COMMA NAME ASSIGN NAME)* RPAREN)? -> ^(DEFFUNCMODIFIERS NAME*);

block: LCURLY
			block_content*
		RCURLY -> ^(BLOCK block_content*);
block_content: block | compound_stmt;


test_expr: or_test;
or_test: xor_test (OR^ xor_test)*;
xor_test: and_test (XOR^ and_test)*;
and_test: not_test (AND^ not_test)*;
not_test: NOT^ not_test | comparison;

comparison: arith_expr (comp_op^ arith_expr)*;
comp_op: LESS | LESSEQUAL | EQUAL | NOTEQUAL | GREATEREQUAL | GREATER;

expr: test_expr;
arith_expr: term ((PLUS^ | MINUS^) term)*;
term: factor ((STAR^ | SLASH^ | PERCENT^) factor)*;
factor:
	PLUS^ factor
	| MINUS^ factor
	| power;
power: function_operator (DOUBLESTAR power -> ^(DOUBLESTAR function_operator power) | /*nothing*/ -> function_operator);
function_operator:
	(a=atom->$a) (NAME b=atom -> ^(CALLFUNC NAME $a $b))*;

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


