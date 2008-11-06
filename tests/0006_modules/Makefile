LLI=lli
LLVM_LINK=llvm-link
EXOSELF=../../src/exoself



files = $(shell cat $(testnum).app)
sources = $(addsuffix .es, $(files))
objects = $(addsuffix .bc, $(files))

.PHONY: run

run: t$(testnum).bc
	@$(LLI) t$(testnum).bc


t$(testnum).bc: $(objects)
	@$(LLVM_LINK) -o t$(testnum).bc $(objects)


$(objects): $(sources)

%.bc: %.es
	@$(EXOSELF) $<


clean:
	@rm -f t$(testnum).bc $(objects) > /dev/null 2> /dev/null

