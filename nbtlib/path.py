from copy import deepcopy
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
    for i in Int.all_tags.values():
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
            *p,(q,r)=self.parts
            r=r if r is not None else Compound()
            r=deepcopy(r)
            r.merge(key)
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
                j= "" if j is None else j
                if i is not None:
                    if any(k in i for k in " .{}[]\"") or not i:
                        i='"'+("\\\"".join("\\\\" .join(i.split("\\")) .split("\"")))+'"'
                    
                    out+=f"{i}{j!s}."
                else:
                    out+=f"{j!s}."
        return "".join(out)
    def __repr__(self):
        return f"NBT_Path({str(self).__repr__()})"
    def match(self,obj):#NBT_Path("Items[][0].a{}").match(nbtlib.parse_nbt("{Items:[[{a:{}}],[{s:'',a:''}]]}"))
        out=[obj]
        for item in self:
            if isinstance(item,int):
                out_=[]
                for i in (i for i in out if isinstance(i,(List,LongArray,ByteArray,IntArray))):
                    if isinstance(i,List):  
                        try:
                            out_.append(i[item])
                        except:
                            pass
                    elif isinstance(i,LongArray):  
                        try:
                            out_.append(Long(i[item]))
                        except:
                            pass
                    elif isinstance(i,ByteArray):  
                        try:
                            out_.append(Byte(i[item]))
                        except:
                            pass
                    elif isinstance(i,IntArray):  
                        try:
                            out_.append(Int(i[item]))
                        except:
                            pass
                    else:
                        pass
                        
                out=out_
            elif item is None:
                out=[j for i in ( map(Long,i)  if isinstance(i,LongArray) else map(Byte,i) if isinstance(i,ByteArray) else map(Int,i) if isinstance(i,IntArray) else i for i in out if isinstance(i,(List,ByteArray,IntArray,LongArray))) for j in i]
            else:
                itemname,tag=item
                if itemname is not None:
                    out_=[]
                    for i in (i for i in out if isinstance(i,Compound)):
                        try:
                              out_.append(i[itemname])
                        except:
                              pass
                    out=out_
                if tag is not None:
                    out=[i for i in out if isinstance(i,Compound) and match(i,tag)]
        return out
    def join(this,that):
        if isinstance(that,str):
            that=type(this)(that)
        if that.parts==((None,None),):
            return this
        if isinstance(that.parts[0],(int,type(None))) or that.parts[0][0] is not None:
            return type(this)(this.parts+that.parts)
        *a,(b,c)=this
        (d,e),*f=that
        c=c if c is not None else Compound()
        c=deepcopy(c)
        c.merge(e)
        return type(this)((*a,(b,c),*f))
    __sub__=join
    __call__=match




'''
nbtlib.path.NBT_Path("Items")[None][-1]["a"].match(nbtlib.parse_nbt("{Items:[[{a:{}}],[{s:'',a:''}]]}"))
>>> a-"{a:{e:5b}}[8]"
NBT_Path('a.[-3].c{a: [1b, 2b]}.d.[].e{a: {e: 5b}}.[8].')
>>> a-"{a:{e:5b}}[8]"-"d"
NBT_Path('a.[-3].c{a: [1b, 2b]}.d.[].e{a: {e: 5b}}.[8].d.')
>>> a-"{a:{e:5b}}[8]"-"[5]"
NBT_Path('a.[-3].c{a: [1b, 2b]}.d.[].e{a: {e: 5b}}.[8].[5].')
>>> a-"{a:{e:5b}}"-"[]d{a:{m:4f}}"
NBT_Path('a.[-3].c{a: [1b, 2b]}.d.[].e{a: {e: 5b}}.[].d{a: {m: 4.0f}}.')
>>> a-"{a:{e:5b}}"-"{a:{m:4f}}"
NBT_Path('a.[-3].c{a: [1b, 2b]}.d.[].e{a: {e: 5b, m: 4.0f}}.')
>>>NBT_Path("Items[].a[]")(nbtlib.parse_nbt("{Items:[{a:[1,2]},{a:[B;3b,4b]},{a:[L;3l,4l]},{a:[I;3,4]},{a:[B;3b,4b]},{a:[\"3\",\"4\"]}]}"))
[Int(1), Int(2), Byte(3), Byte(4), Long(3), Long(4), Int(3), Int(4), Byte(3), Byte(4), String('3'), String('4')]
'''
