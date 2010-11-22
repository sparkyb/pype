#!/usr/bin/python
import time
import os
import re
import keyword

todoexp = re.compile('#([a-zA-Z0-9 ]+):(.*)')

nam = '[a-zA-Z_][a-zA-Z0-9_]+'
typ = '(?:' + nam + '(?:\s+%s)*'%nam + '(?:\s*\[\])*' + '(?:\s*\*)*' + ')*'
clsnam = nam + '::' + '(?:%s|operator(?:\+|-|\*|/|=|<|>|\+=|-=|\*=|/=|<<|>>|<<=|>>=|==|!=|<=|>=|\+\+|--|%%|&|\^|!|\||~|&=|\^=|\|=|&&|\|\||%%=|\[\]|()|new|delete))'%nam
args = '(?:%s\s*%s)*'%(typ,nam) + '(?:\s*,\s*%s\s*%s)*'%(typ,nam)
cfcnre = '(%s)\s+(%s)\s+\(\s*(%s)\s*\)\s*{'%(typ, clsnam, args)

cfcn = re.compile(cfcnre)

ctodoexp = re.compile(r'\\([a-zA-Z0-9 ]+):(.*)')

_kwl = dict.fromkeys(keyword.kwlist)
_kwl.update(dict.fromkeys('http ftp mailto news gopher telnet'.split()))

def detectLineEndings(text):
    crlf_ = text.count('\r\n')
    lf_ = text.count('\n')
    cr_ = text.count('\r')
    mx = max(lf_, cr_)
    if not mx:
        return os.linesep
    elif crlf_ >= mx/2:
        return '\r\n'
    elif lf_ is mx:
        return '\n'
    else:# cr_ is mx:
        return '\r'

def leading(line):
    return len(line)-len(line.lstrip())

def c_parser(source, line_ending, wxYield):
    texp = ctodoexp
    todo = []
    line_no = 0
    for line in source.split(line_ending):
        line_no += 1
        
        ls = line.strip()
        
        if 0:
            pass
        
        elif ls[:2] == '\\':
            r = texp.search(ls)
            if r:
                tpl = r.groups()
                todo.append((tpl[0].strip().lower(),
                             line_no,
                             tpl[1].count('!'),
                             tpl[1].strip()))

def fast_parser(source, line_ending, flat, wxYield):
    texp = todoexp
    kwl = _kwl
    lines = source.split(line_ending)
    docstring = {} #new_kwl()
    todo = []
    
    out = []
    stk = []
    line_no = 0
##    SEQ = ('def ','class ')
    
    FIL = lambda A:A[1][2]

    def fun(i, line, ls, line_no, stk):
        try: wxYield()
        except: pass
        na = ls.find('(')
        ds = ls.find(':')
        if na == -1:
            na = ds
        if na != -1:
            if ds == -1:
                ds = na
            fn = ls[len(i):ds].strip()
            if fn:
                lead = len(line)-len(ls)
                while stk and (stk[-1][2] >= lead):
                    prev = stk.pop()
                    if stk: stk[-1][-1].append(prev)
                    else:   out.append(prev)
                nam = i+fn
                nl = nam.lower()
                f = ls[len(i):na].strip()
                
                if f in ('__init__', '__new__') and len(stk):
                    docstring.setdefault(stk[-1][1][-1], []).append("%s %s.%s"%(fn, '.'.join(map(FIL, stk)), f))
                stk.append((nam, (f.lower(), line_no, f), lead, []))
                docstring.setdefault(f, []).append("%s %s"%(fn, '.'.join(map(FIL, stk))))
                
    
    for line in lines:
        line_no += 1
        ls = line.lstrip()

        if ls[:4] == 'def ':
            fun('def ', line, ls, line_no, stk)
        elif ls[:5] == 'cdef ':
            fun('cdef ', line, ls, line_no, stk)
        elif ls[:6] == 'class ':
            fun('class ', line, ls, line_no, stk)
        elif ls[:1] == '#':
            r = texp.search(ls)
            if r:
                tpl = r.groups()
                if tpl[0].split()[0] not in kwl:
                    todo.append((tpl[0].strip().lower(),
                                 line_no,
                                 tpl[1].count('!'),
                                 tpl[1].strip()))
        #elif ls[:3] == '#>>':
        #    fun('#>>', line, ls, line_no, stk)

    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat == 0:
        return out, docstring.keys()
    elif flat==1:
        return docstring
    elif flat==2:
        return out, docstring.keys(), docstring
    else:
        return out, docstring.keys(), docstring, todo


