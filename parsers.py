#!/usr/bin/python
import time
import compiler
from compiler.ast import Function, Class
import keyword
import os
eol = os.linesep

#def new_kwl():
#    kwl = {}
#    for i in keyword.kwlist:
#        kwl[i] = []
#    return kwl

def detectLineEndings(text):
    crlf_ = text.count('\r\n')
    lf_ = text.count('\n')
    cr_ = text.count('\r')
    mx = max(lf_, cr_)
    if not mx:
        return eol
    elif crlf_ >= mx/2:
        return '\r\n'
    elif lf_ is mx:
        return '\n'
    else:# cr_ is mx:
        return '\r'

def recur_compiled(obj, heir, lines):
    if isinstance(obj, Function) or isinstance(obj, Class):
        h = heir + [obj.name]
        if obj.doc is None:
            docstring = {obj.name: ['']}
        else:
            docstring = {obj.name: [obj.doc]}
        if isinstance(obj, Function):
            n = 'def '+obj.name
            if not obj.doc:
                docstring[obj.name][0] = "%s(%s) %s"%(obj.name, ', '.join(obj.argnames), '.'.join(h))
            if obj.name == '__init__':
                if heir:
                    if heir[-1] in docstring:
                        docstring[heir[-1]].append(docstring[obj.name][0])
                    else:
                        docstring[heir[-1]] = [docstring[obj.name][0]]
        else:# isinstance(obj, Class)
            n = 'class '+obj.name
        out = [(n, (n.lower(), obj.lineno-1), leading(lines[obj.lineno-1]), [])]
        ot = out[0][-1]
    else:
        h = heir
        docstring = {}
        out = []
        ot = out
    for i in obj.getChildNodes():
        o, d = recur_compiled(i, h, lines)
        ot.extend(o)
        for nam, dsl in d.iteritems():
            if nam in docstring: docstring[nam].extend(dsl)
            else: docstring[nam] = dsl
    return out, docstring

def slow_parser(source, line_ending, flat=0):
    #docstring = new_kwl()

    lines = source.split(line_ending)
    mod = compiler.parse(source)
    heir, docstring = recur_compiled(mod, [], lines)
    #for nam, dsl in ds.iteritems():
    #    if nam in docstring: docstring[nam].extend(dsl)
    #    else: docstring[nam] = dsl
    new_ds = {}
    for i,j in docstring.iteritems():
        #pulling out all the unused ones
        new_ds[i] = filter(None, j)

    if flat == 0:
        return heir, new_ds.keys()
    elif flat == 1:
        return new_ds
    else:
        return heir, new_ds.keys(), new_ds

def leading(line):
    cur = 0
    while line[cur:cur+1] == ' ':
        cur += 1
    return cur

def fast_parser(source, line_ending, flat=0):
    lines = source.replace('\t', 8*' ').split(line_ending)
    docstring = {} #new_kwl()
    
    out = []
    stk = []
    line_no = -1
    for line in lines:
        line_no += 1
        ls = line.strip()
        na = ls.find('(')
        if na == -1:
            na = ls.find(':')
        for i, li in [('def ', 4), ('class ', 6)]:
            if ls[:li] == i:
                if na != -1:
                    fn = ls[li:na].strip()
                    if fn:
                        lead = leading(line)
                        while stk and (stk[-1][2] >= lead):
                            prev = stk.pop()
                            if stk: stk[-1][-1].append(prev)
                            else:   out.append(prev)
                        nam = i+fn
                        nl = nam.lower()
                        if not fn in docstring: docstring[fn] = []
                        stk.append([nam, (nl, line_no), lead, []])
                        break
        #else non-function or non-class definition lines
    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat == 0:
        return out, docstring.keys()
    elif flat==1:
        return docstring
    else:
        return out, docstring.keys(), docstring


def tim(p=1, ct = [None]):
    if ct[0] == None:
        ct[0] = time.time()
    else:
        ret = time.time() - ct[0]
        ct[0] = time.time()
        if p: print ret,
        return ret

if __name__ == '__main__':
    import sys, time

    if len(sys.argv)>1:
        fil = open(sys.argv[1], 'r')
        txt = fil.read()
        fil.close()
        tim();print 'fast parser...',
        fast_parser(txt, detectLineEndings(txt))
        tim();print 'done.\nslow parser...',
        a,b,c = slow_parser(txt, detectLineEndings(txt), 2)
        tim();print 'done.'
        import pprint
        pprint.pprint(c)

    else:
        print 'usage:\n python parsers.py <source file>'
