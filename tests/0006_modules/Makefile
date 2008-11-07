LLI=lli
LLVM_LINK=llvm-link
EXOSELF=../../src/exoself
EXOSELF_OPTS=--save-temps



files = $(shell cat $(testnum).app)
sources = $(addsuffix .es, $(files))
objects = $(addsuffix .bc, $(files))

.PHONY: run

run: t$(testnum).bc
	@$(LLI) t$(testnum).bc


t$(testnum).bc: $(objects)
	@$(LLVM_LINK) -f -o t$(testnum).bc $(objects)


$(objects): $(sources)

%.bc: %.es
	@$(EXOSELF) $(EXOSELF_OPTS) $<


clean:
	@rm -f t$(testnum).bc $(objects) > /dev/null 2> /dev/null
	@rm -f $(addsuffix .ast, $(files)) > /dev/null 2> /dev/null
	@rm -f $(addsuffix .preopt.ll, $(files)) > /dev/null 2> /dev/null
	@rm -f $(addsuffix .ll, $(files)) > /dev/null 2> /dev/null

