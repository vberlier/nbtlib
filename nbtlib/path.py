from .tag import *
from .literal.parser import Parser,tokenize
__all__ = ('NBT_Path',)

import re
def slice_nbt(literal):
    parser = Parser(tokenize(literal))
    tag = parser.parse()

    cursor = parser.token_span[1]
    leftover = literal[cursor:]

    return tag,leftover


def match(obj,pattern):
	for i in Base.all_tags.values():
		if isinstance(obj,i) and isinstance(pattern,i):
			break
	else:
		return False
	if i is Compound:
		return all(((k in obj) and match(obj[k],v)) for k,v in pattern.items())
	elif i is List:
		if pattern:
			return all(any(match(k,j) for k in obj) for j in pattern)
		else:
			return not obj
	else:
		return obj==pattern

def parser(string):
    if string.startswith("{"):
        tag,string=slice_nbt(string)
        yield (None,tag)
        
    while string:
        if string.startswith("["):#[]
            r=re.match("\[(-?\d+)?\]\.?",string)
            x=r.groups()[0]
            if x:x=int(x)
            string=string[r.end():]
            yield x
        else:
            if string.startswith('"'):#""
                r=re.match(r'\"((\\\"|\\\\|[^\\\"])*)\"',string)
                t=r.groups()[0]
                t="\"".join("\\".join(t.split("\\\\")).split("\\\""))
                string=string[r.end():]

            else:
                r=re.match('[^\[\]\{\}\. \"]+',string)
                t=r.group()
                string=string[r.end():]
            if string.startswith('{'):
                tag,string=slice_nbt(string)
                yield (t,tag)
            else:
                yield (t,None)
            if string.startswith("."):
                string=string[1:]
        
class NBT_Path(tuple):
    def __new__(cls,args=""):
        args=args or ((None,None),)
        if isinstance(args,str):
            r=(*parser(args),)
        else:
            r=(*args,)
        if len(r)>1 and r[0] == (None,None):
            r=r[1:]
        return tuple.__new__(cls,r)
 
    @property
    def parent(self):
        return type(self)(self.parts[:-1])

    @property
    def parts(self):
        return tuple(self)

    @property
    def name(self):
        try:
            return self.parts[-1][0]
        except:
            return None
        
    def __getitem__(self, key):
        if isinstance(key,int) or key is None:
            return type(self)(self.parts+(key,))
        if isinstance(key,str):
            return type(self)(self.parts+((key,None),))
        if isinstance(key,Compound):
            *p,q=self.parts
            q,r=q
            r=r or Compound()
            r=Compound(r.copy())
            r.update(key)
            return type(self)((*p,(q,r)))
    def __str__(self):
        out=[]
        for item in self:
            
            if isinstance (item,int):
                out +=f"[{item}]."
            elif item is None:
                out+='[].'
            else:
                i,j=item
                i=i or ""
                j= "" if j is None else j
                if any(k in i for k in " .{}[]\""):
                    i='"'+("\\\"".join("\\\\" .join(i.split("\\")) .split("\"")))+'"'
                
                out+=f"{i}{j!s}."
        return "".join(out)
    def __repr__(self):
        return f"NBT_Path({str(self).__repr__()})"#escape?
    def match(self,obj):
        pass
    def join(this,that):
        pass
