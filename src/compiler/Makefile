

JAVA=java
ANTLR_DIR=../../3rdparty/antlr
ANTLR=antlr-3.1.1.jar
ANTLR_CMD=${JAVA} -cp ${ANTLR_DIR}/${ANTLR} org.antlr.Tool



tests: g
	./runtests.py

alltests: g
	./runtests.py -k


g: grammar/exoselfParser.py

grammar/exoselfParser.py: grammar/exoself.g
	${ANTLR_CMD} -o . grammar/exoself.g
	touch grammar/exoselfParser.py
	touch grammar/exoselfLexer.py



