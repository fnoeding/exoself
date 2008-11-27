# 
# The BSD License
# 
# Copyright (c) 2008, Florian Noeding
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
# Neither the name of the of the author nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific
# prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 

package runtime.c
module math


def(mangling=C) cos(_ as float64) as float64;
def(mangling=C) sin(_ as float64) as float64;
def(mangling=C) tan(_ as float64) as float64;

def(mangling=C) acos(_ as float64) as float64;
def(mangling=C) asin(_ as float64) as float64;
def(mangling=C) atan(_ as float64) as float64;
def(mangling=C) atan2(_1 as float64, _2 as float64) as float64;

def(mangling=C) cosh(_ as float64) as float64;
def(mangling=C) sinh(_ as float64) as float64;
def(mangling=C) tanh(_ as float64) as float64;

def(mangling=C) acosh(_ as float64) as float64;
def(mangling=C) asinh(_ as float64) as float64;
def(mangling=C) atanh(_ as float64) as float64;

def(mangling=C) sqrt(_ as float64) as float64;
def(mangling=C) cbrt(_ as float64) as float64;

def(mangling=C) pow(_1 as float64, _2 as float64) as float64;

def(mangling=C) log(_ as float64) as float64;
def(mangling=C) log1p(_ as float64) as float64;
def(mangling=C) log10(_ as float64) as float64;
def(mangling=C) loge(_ as float64) as float64;
def(mangling=C) exp(_ as float64) as float64;
def(mangling=C) expm1(_ as float64) as float64;
def(mangling=C) exp10(_ as float64) as float64;
def(mangling=C) exp2(_ as float64) as float64;

def(mangling=C) ceil(_ as float64) as float64;
def(mangling=C) floor(_ as float64) as float64;

def(mangling=C) fmod(_1 as float64, _2 as float64) as float64;
def(mangling=C) modf(_1 as float64, _2 as float64*) as float64;

def(mangling=C) frexp(_1 as float64, _2 as int32*) as float64;
def(mangling=C) ldexp(_1 as float64, _2 as int32) as float64;


