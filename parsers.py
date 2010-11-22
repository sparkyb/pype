#!/usr/bin/python
import time
import os
import re
import parser
import compiler
import traceback
import symbol
import token
from compiler import ast
from compiler import consts

todoexp = re.compile('#([a-zA-Z0-9 ]+):(.*)', re.DOTALL)

nam = '[a-zA-Z_][a-zA-Z0-9_]+'
typ = '(?:' + nam + '(?:\s+%s)*'%nam + '(?:\s*\[\])*' + '(?:\s*\*)*' + ')*'
clsnam = nam + '::' + '(?:%s|operator(?:\+|-|\*|/|=|<|>|\+=|-=|\*=|/=|<<|>>|<<=|>>=|==|!=|<=|>=|\+\+|--|%%|&|\^|!|\||~|&=|\^=|\|=|&&|\|\||%%=|\[\]|()|new|delete))'%nam
args = '(?:%s\s*%s)*'%(typ,nam) + '(?:\s*,\s*%s\s*%s)*'%(typ,nam)
cfcnre = '(%s)\s+(%s)\s+\(\s*(%s)\s*\)\s*{'%(typ, clsnam, args)

cfcn = re.compile(cfcnre)

_bad_todo = dict.fromkeys('if elif else def cdef class try except finally for while lambda'.split())
_bad_urls = dict.fromkeys('http ftp mailto news gopher telnet file'.split())

def is_url(left, right):
    if left.lstrip().lower() in _bad_urls and right[:2] == '//':
        return 1
    return 0

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

def c_parser(source, line_ending, flat, wxYield):
    texp = todoexp
    todo = []
    line_no = 0
    for line in source.split(line_ending):
        line_no += 1
        ls = line.strip()
        if ls[:2] == '\\':
            r = texp.search(ls)
            if r:
                tpl = r.groups()
                if is_url(*tpl):
                    continue
                todo.append((tpl[0].strip().lower(),
                             line_no,
                             tpl[1].count('!'),
                             tpl[1].strip()))
        #elif ...
    if flat == 0:
        return [], []
    elif flat==1:
        return {}
    elif flat==2:
        return [], [], {}
    else:
        return [], [], {}, todo

def get_definition(lines, line_start):
    cur_line = line_start-1
    ls = lines[cur_line.lstrip()]
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
    
    

def slow_walk_ast(tree):
    transformer = Visitor
    see = dict.fromkeys('Class Function'.split())
    stack = [(tree, 0)]
    while stack:
        tree, seen = stack.pop()
        if not isinstance(tree, ast.Node):
            continue
        name = tree.__class__.__name__
        if name in see:
            if seen:
                yield 'end',
                continue
            
            if hasattr(transformer, 'visit'+name):
                yield 'start', getattr(transformer, 'visit'+name)(tree), tree.lineno
            if tree.doc:
                yield 'doc', tree.doc
            stack.append((tree, 1))
        x = list(tree.getChildren())
        x.reverse()
        for i in x:
            if isinstance(i, ast.Node):
                stack.append((i, 0))

class Visitor:
    def visitClass(self, node):
        return 'class', node.name
    
    def visitFunction(self, node):
        return 'def', node.name

Visitor = Visitor()

def slower_parser(source, _1, flat, _2):
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    try:
        x = compiler.parse(source)
    except:
        #parse error, defer to faster parser
        return faster_parser(source, '\n', flat, _2)
    
    stack = []
    out = []
    docstring = {}
    
    defs = get_defs(source)
    
    lines = source.split('\n')
    
    def finalize():
        event, contents = stack.pop()
        doc = ''
        cont = []
        for i in contents:
            if i[0] == 'doc':
                doc = i[1]
            else:
                cont.append(i)
        lineno = event[-1]
        line = lines[lineno-1]
        name = event[1][1]
        names = [i[0][1][1] for i in stack]
        
        h = name
        if lineno in defs:
            h = defs[lineno].split(None, 1)[-1]
        names.append(h)
        doc = '%s\n%s'%('.'.join(names), doc)
        doc = doc.strip()
        docstring.setdefault(name, []).append(doc)
        
        if stack and name in ('__init__', '__new__'):
            parentname = stack[-1][0][1][1]
            docstring.setdefault(parentname, []).append(doc)
        
        #line is where the definition occurs...
        item = (defs.get(lineno, name),
                (name.lower(), lineno, name),
                len(line)-len(line.lstrip()),
                cont)
        if stack:
            stack[-1][-1].append(item)
        else:
            out.append(item)
    
    try:
        for event in slow_walk_ast(x):
            if event[0] == 'start':
                stack.append((event, []))
            elif event[0] == 'doc':
                if stack:
                    stack[-1][-1].append(event)
            elif event[0] == 'end':
                finalize()
    except Exception, why:
        traceback.print_exc()
        return faster_parser(source, '\n', flat, _2)
    
    texp = todoexp
    bad_todo = _bad_todo
    todo = []
    for line_no, line in enumerate(lines):
        ls = line.lstrip()
        if ls[:1] == '#':
            r = texp.match(ls)
            if r:
                tpl = r.groups()
                if tpl[0].split()[0] not in bad_todo and not is_url(*tpl):
                    todo.append((tpl[0].strip().lower(),
                            line_no+1,
                            tpl[1].count('!'),
                            tpl[1].strip()))
    
    return out, docstring.keys(), docstring, todo
#
def get_defs(source, p=0):
    if p:
        pprint.pprint(parser.suite(source).tolist(1))
    
    DATA = 0
    START = 1
    END = 2
    def parse(item):
        if item[0] <= token.N_TOKENS:
            yield DATA, item[1], item[2]
        else:
            li = len(item)
            xtra = None
            if isinstance(item[-1], (int, long)):
                xtra = item[-1]
                li -= 1
            yield START, item[0], xtra
            for i in xrange(1, li):
                for j in parse(item[i]):
                    yield j
            yield END, item[0]
    
    stk = []
    stk2 = []
    stk3 = []
    ret = {}
    inf = 1e155*1e155
    for node in parse(parser.suite(source).tolist(1)):
        if node[0] == DATA and stk:
            sp = ''
            if stk[-1][-1:] == ',' or stk[-1] in ('def', 'class'):
                sp = ' '
            stk[-1] += sp + node[1]
            stk2[-1] = min(stk2[-1], node[2])
        elif node[0] == START:
            if node[1] in (symbol.funcdef, symbol.classdef):
                if node[1] in (symbol.funcdef, symbol.classdef):
                    stk2.append(inf)
                stk.append('')
            elif node[1] == symbol.suite and stk:
                ret[stk2.pop()] = stk.pop().rstrip(':')
        ## elif node[0] == END:
            ## if node[1] in (symbol.parameters,):#, symbol.testlist):
                ## x = stk.pop()
                ## stk[-1] += x
                ## if node[1] == symbol.testlist:
                    ## stk[-1] += ')'
                ## ret[stk2.pop()] = stk.pop()
    if p:
        print
        print stk, stk2
        print
    return ret

def faster_parser(source, line_ending, flat, wxYield):
    texp = todoexp
    bad_todo = _bad_todo
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
                if tpl[0].split()[0] not in bad_todo and not is_url(*tpl):
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

def fast_parser(*args, **kwargs):
    return slower_parser(*args, **kwargs)

'''
([('def foo(x, y=6, *args, **kwargs)', ('foo', 5, 'foo'), 0, []),
  ('class bar',
   ('bar', 9, 'bar'),
   0,
   [('def __init__(self, foo=a, bar={1:2})',
     ('__init__', 10, '__init__'),
     4,
     [])]),
  ('class Baz(object, int)',
   ('baz', 13, 'Baz'),
   0,
   [('def __init__(self, bar=(lambda:None))',
     ('__init__', 14, '__init__'),
     4,
     [('def goo()', ('goo', 16, 'goo'), 8, [])])])],
 '''

## (full, (lower, lineno, upper), indent, contents)

def latex_parser(source, line_ending, flat, _):
    texp = todoexp
    lines = source.split(line_ending)
    todo = []
    out = []
    stk = []
    line_no = 0
    sections = ('\\section', '\\subsection', '\\subsubsection')
    
    def f(which, line, ls, line_no, stk):
        if which in sections:
            ind = which.count('sub')
        elif stk:
            ind = 3
        else:
            ind = -1
        while stk and stk[-1][2] >= ind:
            it = stk.pop()
            if stk:
                stk[-1][-1].append(it)
            else:
                out.append(it)
        na = ls.find('{')
        ds = ls.find('}')
        if na > 0 and ds > 0:
            name = ls[na+1:ds].strip()
            if ind >= 0:
                stk.append((ls.rstrip(), (name.lower(), line_no, name), ind, []))
            else:
                out.append((ls.rstrip(), (name.lower(), line_no, name), 0, []))
    
    for line in lines:
        line_no += 1
        ls = line.lstrip()
        
        if ls[:1] == '%':
            r = texp.search(ls, 1)
            if r:
                tpl = r.groups()
                if is_url(*tpl):
                    continue
                todo.append((tpl[0].strip().lower(),
                             line_no,
                             tpl[1].count('!'),
                             tpl[1].strip()))
            continue
        elif ls[:6] == '\\label':
            f('\\label', line, ls, line_no, stk)
        for i in sections:
            if ls[:len(i)] == i:
                f(i, line, ls, line_no, stk)
                break
                
        

    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat == 0:
        return out, []
    elif flat==1:
        return {}
    elif flat==2:
        return out, [], {}
    else:
        return out, [], {}, todo

if __name__ == '__main__':
    a = '''import a, b, c

#todo: hello world

def foo(x, y=6, *args,
        **kwargs):
    return None

class bar:
    def __init__(self, foo=a, bar={1:2}):
        """blah!"""

class Baz(object, int):
    def __init__(self, bar=(lambda:None)):
        """blah 2"""
        def goo():
            pass
'''
    import pprint
    ## pprint.pprint(get_defs(a,1))
    pprint.pprint(slower_parser(a, '\n', 3, lambda:None)[-1])
