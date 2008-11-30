/* 
* The BSD License
* 
* Copyright (c) 2008, Florian Noeding
* All rights reserved.
* 
* Redistribution and use in source and binary forms, with or without modification,
* are permitted provided that the following conditions are met:
* 
* Redistributions of source code must retain the above copyright notice, this
* list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice, this
* list of conditions and the following disclaimer in the documentation and/or
* other materials provided with the distribution.
* Neither the name of the of the author nor the names of its contributors may be
* used to endorse or promote products derived from this software without specific
* prior written permission.
* 
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
* ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
* ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

def(mangling=C) formatFloat32(buffer as byte*, size as word, format as byte*, v as float32) as void;
def(mangling=C) formatFloat64(buffer as byte*, size as word, format as byte*, v as float64) as void;
def(mangling=C) formatInt32(buffer as byte*, size as word, format as byte*, v as int32) as void;
def(mangling=C) formatInt64(buffer as byte*, size as word, format as byte*, v as int64) as void;
def(mangling=C) formatUInt32(buffer as byte*, size as word, format as byte*, v as uint32) as void;
def(mangling=C) formatUInt64(buffer as byte*, size as word, format as byte*, v as uint64) as void;

def format(buffer as byte*, size as word, format_ as byte*, v as float32) as void
{
	formatFloat32(buffer, size, format_, v);
}

def format(buffer as byte*, size as word, format_ as byte*, v as float64) as void
{
	formatFloat64(buffer, size, format_, v);
}

def format(buffer as byte*, size as word, format_ as byte*, v as int32) as void
{
	formatInt32(buffer, size, format_, v);
}

def format(buffer as byte*, size as word, format_ as byte*, v as int64) as void
{
	formatInt64(buffer, size, format_, v);
}

def format(buffer as byte*, size as word, format_ as byte*, v as uint32) as void
{
	formatUInt32(buffer, size, format_, v);
}

def format(buffer as byte*, size as word, format_ as byte*, v as uint64) as void
{
	formatUInt64(buffer, size, format_, v);
}


