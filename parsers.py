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

def recur_compiled(obj, hier, lines):
    if isinstance(obj, Function) or isinstance(obj, Class):
        h = hier + [obj.name]
        docstring = {obj.name:[]}
        if obj.doc:
            docstring[obj.name].append(obj.doc)
        if isinstance(obj, Function):
            docstring[obj.name].append("%s(%s) %s"%(obj.name, ', '.join(obj.argnames), '.'.join(h)))
            n = "def %s(%s)"%(obj.name, ', '.join(obj.argnames))
            if obj.name == '__init__':
                if hier:
                    docstring.setdefault(heir[-1], []).extend(docstring[obj.name])
        else:# isinstance(obj, Class)
            if obj.bases:
                n = 'class %s(%s)'%(obj.name, ', '.join(obj.bases))
            else:
                n = 'class '+obj.name
        out = [(n, (obj.name.lower(), obj.lineno-1), leading(lines[obj.lineno-1]), [])]
        ot = out[0][-1]
    else:
        h = hier
        docstring = {}
        out = []
        ot = out
    for i in obj.getChildNodes():
        o, d = recur_compiled(i, h, lines)
        ot.extend(o)
        for nam, dsl in d.iteritems():
            docstring.setdefault(nam, []).extend(dsl)
    return out, docstring

def slow_parser(source, line_ending, flat=0):
    #docstring = new_kwl()

    lines = source.split(line_ending)
    mod = compiler.parse(source)
    hier, docstring = recur_compiled(mod, [], lines)
    #for nam, dsl in ds.iteritems():
    #    if nam in docstring: docstring[nam].extend(dsl)
    #    else: docstring[nam] = dsl
    new_ds = {}
    for i,j in docstring.iteritems():
        #pulling out all the unused ones
        new_ds[i] = filter(None, j)

    if flat == 0:
        return hier, new_ds.keys()
    elif flat == 1:
        return new_ds
    elif flat == 2:
        return hier, new_ds.keys(), new_ds
    else:
        return hier, new_ds.keys(), new_ds, []

def leading(line):
    return len(line)-len(line.lstrip())

def fast_parser(source, line_ending, flat=0):
    lines = source.split(line_ending)
    docstring = {} #new_kwl()
    todo = []
    
    out = []
    stk = []
    line_no = -1
##    SEQ = ('def ','class ')
    
    FIL = lambda A:A[1][2]

    def fun(i, line, ls, line_no, stk):
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
                stk.append((nam, (f.lower(), line_no, f), lead, []))
                docstring.setdefault(f, []).append(" ".join([fn, '.'.join(map(FIL, stk))]))
    
    for line in lines:
        line_no += 1
        ls = line.lstrip()
        
        #this method is actually the fastest for the
        #single-pass method, but only by ~1%
        #the other versions are easier to maintain
##        if ls[:4] == 'def ':
##            i = 'def '
##            na = ls.find('(')
##            if na == -1:
##                na = ls.find(':')
##            if na != -1:
##                fn = ls[len(i):na].strip()
##                if fn:
##                    lead = len(line)-len(ls)#Leading(None, line, i)
##                    while stk and (stk[-1][2] >= lead):
##                        prev = stk.pop()
##                        if stk: stk[-1][-1].append(prev)
##                        else:   out.append(prev)
##                    nam = i+fn
##                    nl = nam.lower()
##                    docstring[fn] = []
##                    stk.append((nam, (nl, line_no), lead, []))
##        elif ls[:6] == 'class ':
##            i = 'class '
##            na = ls.find('(')
##            if na == -1:
##                na = ls.find(':')
##            if na != -1:
##                fn = ls[len(i):na].strip()
##                if fn:
##                    lead = len(line)-len(ls)#Leading(None, line, i)
##                    while stk and (stk[-1][2] >= lead):
##                        prev = stk.pop()
##                        if stk: stk[-1][-1].append(prev)
##                        else:   out.append(prev)
##                    nam = i+fn
##                    nl = nam.lower()
##                    docstring[fn] = []
##                    stk.append((nam, (nl, line_no), lead, []))

        if ls[:4] == 'def ':
            fun('def ', line, ls, line_no, stk)
        elif ls[:6] == 'class ':
            fun('class ', line, ls, line_no, stk)
        elif ls[:1] == '#':
            a = ls.lower().find('todo:')
            if a+1:
                todo.append((line_no, ls.count('!'), ls[a+5:].strip()))
        #elif ls[:3] == '#>>':
        #    fun('#>>', line, ls, line_no, stk)

##        if ls.startswith('def '):
##            fun('def ', line, ls, line_no, stk)
##        elif ls.startswith('class '):
##            fun('class ', line, ls, line_no, stk)

##        for i in SEQ:
##            if ls[:len(i)] == i:
##                fun(i, line, ls, line_no, stk)
##                break
        #else non-function or non-class definition lines
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

def tim(p=1, ct = [None]):
    if ct[0] == None:
        ct[0] = time.time()
    else:
        ret = time.time() - ct[0]
        ct[0] = time.time()
        if p: print ret,
        return ret

def test():
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

def main():
    import fileinput
    import sys
    import os
    
    lines = []
    fil = '-'
    if len(sys.argv)>1 and sys.argv[-1]:
        fil = os.path.normpath(sys.argv[-1])
        a = open(fil, 'rb')
        toparse = a.read()
        a.close()
    else:
        for line in fileinput.input(fil):
            lines.append(line)
        toparse = ''.join(lines)
    toparse = eval(toparse)
    le = detectLineEndings(toparse)
    toprint = fast_parser(toparse, le, 3)
    
##    try:
##        raise ''
##        if len(toparse) > (1024*512):
##            raise ''
##        toprint = slow_parser(toparse, le, 3)
##    except:
##        toprint = fast_parser(toparse, le, 3)
    if fil == '-':
        print repr(toprint)
    else:
        os.remove(fil)
        a = open("%s.out"%fil, 'w')
        a.write(repr(toprint))
        a.close()

if __name__ == '__main__':
    main()
