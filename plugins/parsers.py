#!/usr/bin/python
import bisect
import compiler
import compiler.ast
import os
import parser
import pprint
import re
import time
import token
import traceback
import symbol

from plugins import exparse

todoexp = re.compile('(>?[a-zA-Z0-9 ]+):(.*)', re.DOTALL)

_bad_todo = dict.fromkeys('if elif else def cdef class try except finally for while lambda with'.split())
_bad_urls = dict.fromkeys('http ftp mailto news gopher telnet file'.split())

try:
    _pype
except:
    class _pype:
        STRICT_TODO = 0

def is_url(left, right, ml=0):
    if left.lstrip().lower() in _bad_urls and right[:2] == '//':
        return 1
    if not ml and _pype.STRICT_TODO and left[:1] != '>':
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

def detectLineIndent(lines, use_tabs, spaces_per_tab, spaces_per_indent):
    tablines = 0
    lc = 0
    prev = 0, 0
    deltas = {}
    for line in lines:
        line = line.rstrip('\r\n')
        tl = 0
        ll = len(line)
        indent = ll-len(line.lstrip())
        lc += 1
        leading = line[:indent]
        if '\t' in leading:
            # we've definitely got tab indents,
            # but is it mixed, or straight up
            # tabs, or are the tabs a mistake?
            leading = leading.replace('\t', '')
            tl = indent - len(leading)
            tablines += 1
        ind = len(leading)
        this = tl, ind
        if prev == this:
            # multiple lines of the same indent
            # level isn't very interesting, we
            # only care about transitions
            continue
        x = (0,)
        if tl or prev[0]:
            # 1, 2, 3, and 7 spaces per tab is strange...but we'll
            # check them just to be sure
           x = (0, 1, 2, 3, 4, 6, 8)
        for i in x:
            d = abs((ind + i*tl) - (prev[1] + i*prev[0]))
            deltas[i,d] = deltas.get((i,d), 0) + 1
        prev = this
    # We have counts of transitions between different indent levels.
    # The correct one will generally dominate, and will also divide
    # the other major indent levels evenly.
    if deltas:
        # if more than 1/8 of your lines have tabs...you probably used tabs
        need_tabs = tablines > lc / 8
        for count, (sppt, delta) in sorted(((j,i) for i,j in deltas.iteritems()), reverse=True):
            # Unless something funky is going on, the maximum is the likely
            # correct answer, so we'll use it unless we are supposed to use tabs...
            if not sppt and need_tabs:
                continue
            spaces_per_indent = delta
            use_tabs = bool(sppt)
            if use_tabs:
                spaces_per_tab = sppt
            break
    return use_tabs, spaces_per_tab, spaces_per_indent

def leading(line):
    return len(line)-len(line.lstrip())

def line_info(lineno):
    return exparse.Info(lineno, '\xff', '\xff', 999, 999, (), (), "", 999999999)

#------------------------------- C/C++ parser --------------------------------

defn = '(?:is+)*(?:is+\*+s+)?(?:is*::s*)?cs*\(a\)\s*{'
rep = [('a', '(?:\b|b|b(?:,s*b)*)'),
       ('b', '(?:i?[ \t\*&]*is*(?:\[[^\]]*\])*)'),
       ('c', '(?:i|operator[^\w]+)'),
       ('d', '(?:(?:is+)*(?:is+\*+s+)?is*;f*)'),
       ('i', '(?:[a-zA-Z_]\w*)'),
       ('s', '[ \t]'),
       ('f', '\s'),
       ('y', '(?:[dD][eE][fF][iI][nN][eE])')]

fcn = '(#ys+i\(i(?:,s*i)*\))|(?:(cs*\([^\)]*\))[^{;\)]*[;{])'
sdef = '(c)s*\('

for i,j in rep:
    try:
        _ = re.compile(j)
    except:
        print j
        raise
    fcn = fcn.replace(i,j)
    sdef = sdef.replace(i,j)

fcnre = re.compile(fcn)
sdefre = re.compile(sdef)

badstarts = []
for i in 'if for while switch case return'.split():
    badstarts.append(i+'(')
    badstarts.append(i+' ')
    badstarts.append(i+'\t')

ops = '+-=<>?%!~^&(|/"\''

def _get_tags(out, todo):
    #tags: ^tag parser
    out = _flatten2(out)
    out = [i for i in out if not i[1].startswith('-- ')] #line_no, defn
    rtags = {'':dict(out)}
    todo = [i for i in todo if i[0] == 'tags'] #tag, line_no, excl, content
    tags = []
    last = None
    while todo and out:
        if todo[-1][1] == out[-1][0]:
            #tag line matches parsed line, maybe it hangs out to the right?
            _ = todo.pop()
            tags.append((out[-1][0], _[-1], out[-1][1]))
        
        elif out[-1][0] > todo[-1][1]:
            last = out.pop()
        
        elif '^' in todo[-1][3]:
            _ = todo.pop()
            tags.append((out[-1][0], _[-1], out[-1][1]))
        
        else:
            #todo is > out, use last if it exists
            _ = todo.pop()
            if last:
                tags.append((last[0], _[-1], last[1]))
            else:
                tags.append((_[1], _[-1], "?"))
    
    for line, content, defn in tags:
        for tag in re.split("[^0-9a-z]+", content.lower()):
            if not tag:
                continue
            if tag not in rtags:
                rtags[tag] = {}
            rtags[tag][line] = defn
    
    return rtags

def _shared_parse(ls, todo, line_no, bad_todo=(), start=1, texp=todoexp, ml=0):
    r = texp.match(ls, start)
    if not r:
        return 0
    tpl = r.groups()
    if (tpl[0].split() or [''])[0] in bad_todo or is_url(tpl[0], tpl[1], ml):
        return 0
    if tpl[0][:1] == '>':
        tpl = tpl[0][1:], tpl[1]
    todo.append((tpl[0].strip().lower(),
            line_no,
            tpl[1].count('!'),
            tpl[1].strip()))
    return 1

def c_parser(source, line_ending, flat, wxYield):
    posn = 0
    lc = 1
    post = 0
    out = []
    docs = {}
    for i in fcnre.finditer(source):
        fcn = i.group(0).replace('\n', ' ')
        
        #update line count
        lc += post + source.count('\n', posn, i.start())
        post = 0
        post = source.count('\n', i.start(), i.end())
        posn = i.end()
        
        sm = sdefre.search(fcn)
        short = sm.group(1)
        
        #check for function-like macros
        if fcn.lower().startswith('#define'):
            out.append((fcn, (short.lower(), lc, short), 0, []))
            docs.setdefault(short, []).append(fcn[sm.start():])
            continue
        
        #handle the 'badstarts'
        cont = 0
        for j in badstarts:
            if fcn.startswith(j):
                cont = 1
                break
        if cont:
            continue
        
        #handle function calls
        pp = fcn.rfind(')')
        if fcn.endswith(';'):
            xx = fcn[pp+1:-1]
            if not xx.strip():
                continue
            for j in ops:
                if j in xx:
                    cont = 1
                    break
            if cont:
                continue
        
        #get the start of the definition
        linestart = source.rfind('\n', 0, i.start()) + 1 #yes, I really want this
        
        fcns = source[linestart:i.start()]
        dfcns = dict.fromkeys(fcns)
        
        #check for operators in the beginning; for things like...
        #x = fcncall(...) * X;
        for j in ops:
            if j in dfcns:
                cont = 1
                break
        if cont:
            continue
        
        if '[' not in short:
            docs.setdefault(short, []).append(fcn[sm.start():pp+1])
        #use the entire definition
        fcn = ' '.join(fcns.split() + fcn[:pp+1].split())
        out.append((fcn, (short.lower(), lc, short), 0, []))
    
    texp = todoexp
    todo = []
    _sp = _shared_parse
    labels = []
    lines = source.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for line_no, line in enumerate(lines):
        ls = line.strip()
        if ls[:2] == '//':
            _sp(ls, todo, line_no+1, start=2)
        elif ls[:2] == '/*' and ls[-2:] == '*/':
            _label(ls.strip('/* '), labels, line_no+1)
    
    out, docs = exparse.translate_old_to_new(out, docs, len(lines))
    
    if labels:
        add_labels(out, labels)
    
    return out, docs.keys(), docs, todo

#-------------------------------- misc stuff ---------------------------------

def _flatten(out, seq=None):
    #used for:
    #------ labels like this one ------
    first = 0
    if seq is None:
        seq = []
        first = 1
    
    for i,j in enumerate(out):
        ## print j[1], j[2]
        seq.append((j[1][1], i, out, j[2]))
        if j[-1]:
            _flatten(j[-1], seq)
    if first:
        seq.append((0x7fffffff, len(seq), out, 0))
    return seq

def _flatten2(out, seq=None):
    #used for:
    #tags: like this one^
    #tags: ^tag parser
    first = 0
    if seq is None:
        seq = []
        first = 1
    for i,j in enumerate(out):
        seq.append((j[1][1], j[0]))
        if j[-1]:
            _flatten2(j[-1], seq)
    return seq

def add_labels(out, labels):
    if USE_NEW:
        for label in labels:
            posn = bisect.bisect_right(out, label)
            line_no, indent, text = label
            dl = '-- ' + text + ' --'
            if len(out) > posn and out[posn-1].depth <= out[posn].depth:
                # no children on the previous guy
                # or there are children on the previous guy
                # either way, take the depth of the next guy...
                out.insert(posn, exparse.Info(line_no, text, dl, out[posn].depth, indent, (), None, None, 1, dl, dl))
                continue
            # We should iterate up the set of contexts to try to find the
            # proper indent level...but screw that; we'll just toss it in as a
            # sibling to make navigation easier.
            out.insert(posn, exparse.Info(line_no, text, dl, out[posn-1].depth, indent, (), None, None, 1, dl, dl))
    else:
        labels.reverse()
        seq = _flatten(out)
        seq.reverse()
        _ = seq[-1]
        while labels:
            #'seq and' portion semantically unnecessary
            line, label = labels.pop()
            while seq and line > seq[-1][0]:
                _ = seq.pop()
            __, posn, entry, indent = seq[-1]
            #normalize the label
            entry.insert(posn, ('-- %s --'%label, (label.lower(), line, label), indent, []))

def _label(lss, labels, line_no, indent=None):
    #we may have a label of the form...
    # ----- label -----
    if len(lss) > 4 and lss[:1] == lss[-1:] == '-':
        labels.append((line_no, lss.strip('\t\n\x0b\x0c\r -')))

def _new_label(lss, labels, line_no, indent):
    #we may have a label of the form...
    # ----- label -----
    if len(lss) > 4 and lss[:1] == lss[-1:] == '-':
        labels.append((line_no, indent, lss.strip('\t\n\x0b\x0c\r -')))

#------------------------------ Python parsers -------------------------------

def slower_parser(source, _1, flat, _2):
    try:
        if USE_NEW:
            out, docstring = exparse._parse(source)
        else:
            out, docstring = exparse.parse(source)
    except:
        import traceback
        traceback.print_exc()
        #parse error, defer to faster parser
        return faster_parser(source, '\n', flat, _2)

    texp = todoexp
    bad_todo = _bad_todo
    todo = []
    _sp = _shared_parse
    labels = []
    _l = _label
    if USE_NEW:
        _l = _new_label
    for line_no, line in enumerate(source.split('\n')):
        if '#' not in line:
            continue
        p = line.find('#')
        if not _sp(line[p:], todo, line_no+1, bad_todo, 1+(line[p+1:p+2]=='#')):
            _l(line[p+1:].lstrip('#>'), labels, line_no+1, len(line)-len(line.lstrip()))
    
    if labels:
        add_labels(out, labels)
    
    return out, docstring.keys(), docstring, todo
#
def faster_parser(source, line_ending, flat, wxYield):
    texp = todoexp
    bad_todo = _bad_todo
    lines = source.split(line_ending)
    docstring = {} #new_kwl()
    todo = []
    
    out = []
    stk = []
    if USE_NEW:
        stk.append(exparse.Info(-1, '', '', 0, -1, (), None, None, len(lines)))
    line_no = 0
    _len = len
    
    FIL = lambda A:A[1][2]
    if USE_NEW:
        FIL = lambda A:A[1]
    
    def fun(i, line, ls, line_no, stk):
        ## try: wxYield()
        ## except: pass
        na = ls.find('(')
        ds = ls.find(':')
        if na == -1:
            na = ds
        if na != -1:
            if ds == -1:
                ds = na
            fn = ls[_len(i):ds].strip()
            if fn:
                lead = _len(line)-_len(ls)
                if USE_NEW:
                    while stk and (stk[-1][4] >= lead):
                        stk[-1].lines = line_no - stk[-1].lineno
                        out.append(stk.pop())
                else:
                    while stk and (stk[-1][2] >= lead):
                        prev = stk.pop()
                        if stk: stk[-1][-1].append(prev)
                        else:   out.append(prev)
                nam = i+fn
                nl = nam.lower()
                f = ls[_len(i):na].strip()
                
                if f in ('__init__', '__new__') and _len(stk):
                    key = stk[-1][1]
                    if not USE_NEW:
                        key = key[2]
                    docstring.setdefault(key, []).append("%s %s.%s"%(fn, '.'.join(map(FIL, stk)), f))
                if USE_NEW:
                    stk.append(exparse.Info(line_no, f, nam, len(stk), lead, (), None, None, -1))
                else:
                    stk.append((nam, (f.lower(), line_no, f), lead, []))
                docstring.setdefault(f, []).append("%s %s"%(fn, '.'.join(map(FIL, stk))))
    
    _sp = _shared_parse
    _l = _label
    if USE_NEW:
        _l = _new_label
    labels = []
    for line in lines:
        line_no += 1
        ls = line.lstrip()

        if ls[:4] == 'def ':
            fun('def ', line, ls, line_no, stk)
        elif ls[:5] == 'cdef ':
            fun('cdef ', line, ls, line_no, stk)
        elif ls[:6] == 'class ':
            fun('class ', line, ls, line_no, stk)
        elif '#' in line:
            p = line.find('#')
            if not _sp(line[p:], todo, line_no+1, bad_todo, 1+(line[p+1:p+2]=='#')):
                _l(line[p+1:].lstrip('#>'), labels, line_no+1, _len(line)-_len(ls))

    if not USE_NEW:
        while _len(stk) > 1:
            a = stk.pop()
            stk[-1][-1].append(a)
        out.extend(stk)
    else:
        for i in stk:
            i.lines = line_no - i.lineno + (i.lineno >= 0)
        out.extend(stk)
        out.sort()
        exparse._fixup_extra(out)
    
    if labels:
        add_labels(out, labels)
    
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

#-------------------------- spitfire/cheetah parser --------------------------

def cheetah_parser(source, line_ending, flat, _):
    bad_todo = _bad_todo
    _sp = _shared_parse
    _l = _label
    if USE_NEW:
        _l = _new_label
    _len = len
    # because of start/end stuff, for the new parser, we can generate good
    # line count information...we'll do that later
    new_blocks = set('#' + i for i in ('block', 'def')) # to bypass the cheetah parser detection
    todo = []
    labels = []
    docs = {}
    out = []
    stk = []
    lines = source.split('\n')
    for i, line in enumerate(lines):
        ls = line.lstrip()
        if not ls:
            continue
        lead = line.split(None, 1)
        if lead[0] in new_blocks:
            defn = ls.rstrip()
            if len(lead) < 2:
                name = ''
            elif lead[0][0] == '#' and lead[0][1:] == 'block': # to bypass the cheetah parser detection
                name = lead[1].split()[0]
            else:
                name = lead[1].split('#', 1)[0]
            docname = '.'.join(i[1][2] for i in stk)
            if docname:
                docname += '.'
            docname += name
            docs.setdefault(docname, []).append(defn)
            stk.append((defn, (name.lower(), i+1, name), _len(line)-_len(ls), []))
        elif lead[0] == '#end' and len(lead) > 1 and (lead[1][:3] == 'def' or lead[1][:5] == 'block'):
            o = stk.pop()
            if stk:
                stk[-1][-1].append(o)
            else:
                out.append(o)
        elif '#' in line:
            # try to find a todo as best we can...
            pp = 0
            while line.find('#', pp) >= 0:
                pp = line.find('#', pp)
                if _sp(line[pp:], todo, i+1, bad_todo, 1+(line[pp+1:pp+2]=='#')):
                    break
                pp += 1+(line[pp+1:pp+2]=='#')
            else:
                # otherwise try to find a label of the form # --- label ---
                if '---' in line:
                    p = line.find('#')
                    _l(line[p+1:].lstrip('#>'), labels, i+1, _len(line)-_len(ls))
    while len(stk) > 1:
        o = stk.pop()
        stk[-1][-1].append(o)
    out.extend(stk)
    
    if USE_NEW:
        out, docs = exparse.translate_old_to_new(out, docs, len(lines))
    
    if labels:
        add_labels(out, labels)
    
    if flat == 0:
        return out, docs.keys()
    elif flat==1:
        return docs
    elif flat==2:
        return out, docs.keys(), docs
    else:
        return out, docs.keys(), docs, todo

#------------------------------- latex parser --------------------------------

def latex_parser(source, line_ending, flat, _):
    texp = todoexp
    lines = source.split(line_ending)
    todo = []
    out = []
    stk = []
    line_no = 0
    sections = ('\\chapter', '\\section', '\\subsection', '\\subsubsection')
    
    def f(which, line, ls, line_no, stk):
        if which in sections:
            ind = which.count('sub') + which.endswith('section')
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
    
    _sp = _shared_parse
    labels = []
    for line in lines:
        line_no += 1
        ls = line.lstrip()
        
        if ls[:1] == '%':
            if not _sp(ls, todo, line_no, start=1):
                _label(ls.strip('%>'), labels, line_no)
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
    
    if USE_NEW:
        out, _ = exparse.translate_old_to_new(out, {}, len(lines))
    
    if labels:
        add_labels(out, labels)
    
    if flat == 0:
        return out, []
    elif flat==1:
        return {}
    elif flat==2:
        return out, [], {}
    else:
        return out, [], {}, todo

#---------------------------- [ht|x|sg]ml parser -----------------------------

#Are there any other non-opening tags?
no_ends = []
for i in ('br p input img area base basefont '
          'col frame hr isindex meta param').split():
    no_ends.append(i+' ')
    no_ends.append(i+'>')
    no_ends.append('/'+i+' ')
    no_ends.append('/'+i+'>')

def ml_parser(source, line_ending, flat, _):
    todo = []
    texp = todoexp
    bad_todo = _bad_todo
    _sp = _shared_parse
    labels = []
    for line_no, line in enumerate(source.split(line_ending)):
        if '<!-- ' not in line or ' -->' not in line:
            continue
        
        posn1 = line.find('<!-- ')
        if posn1 == -1:
            posn2 == -2
        else:
            posn2 = line.find(' -->', posn1)
        
        if posn1 > posn2:
            continue
        
        r = texp.match(line, posn1+5, posn2)
        
        if not r:
            _label(line[posn1+5:posn2], labels, line_no+1)
        else:
            _sp(r.group(), todo, line_no+1, bad_todo, 0, ml=1)
    
    out = []
    if labels:
        add_labels(out, labels)
    
    if flat == 0:
        return out, []
    elif flat==1:
        return {}
    elif flat==2:
        return out, [], {}
    else:
        return out, [], {}, todo

#--------------------------- other misc functions ----------------------------

def preorder(h):
    #uses call stack; do we care?
    for i in h:
        yield i[1][2], i
        for j in preorder(i[3]):
            yield j

def _preorder(h):
    #uses explicit stack, may be slower, no limit to depth
    s = [h]
    while s:
        c = s.pop()
        yield c[1][2]
        s.extend(c[3][::-1])

_name_start = dict.fromkeys(iter('abcdefghijklmnopqrstuvwxyzABCDEFGHIJLKMNOPQRSTUVWXYZ_'))
_name_characters = dict(_name_start)
_name_characters.update(dict.fromkeys(iter('0123456789')))

def get_last_word(line):
    nch = _name_characters
    for i in xrange(len(line)):
        if line[-1-i] not in nch:
            break
    
    if line[-1-i] in _name_start:
        #handles a word that is the whole line
        return line[-1-i:]
    ## if i and line[-i] in _name_start and line[-1-i] in :
        ## #handles a word that isn't the whole line
        ## return line[-i:]
    return ''

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

if __name__ == '__main__':
    a = '''import a, b, c

#todo: hello world

def foo(x, y=6, *args,
        **kwargs):
    return None

class bar:
    #--- this is also a label ---
    def __init__(self, foo=a, bar={1:2}):
        #--- this is a label! ---
        """blah!"""

class Baz(object, int):
    def __init__(self, bar=(lambda:None)):
        """blah 2"""
        def goo():
            pass
'''
    ## pprint.pprint(get_defs(a,1))
    pprint.pprint(slower_parser(a, '\n', 3, lambda:None))
