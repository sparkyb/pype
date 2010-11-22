#!/usr/bin/python

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

def slow_parser(source, extra=None):
    import parser, keyword
    kw = dict(zip(keyword.kwlist[:], len(keyword.kwlist)*[0]))
    cd = {'class':1, 'def':1}
    #Apparently the parser module has some problems with non \n line endings.
    #It really shouldn't, but apparently it does.  It was having some problems
    #with PyPE and a half-dozen other pieces of python source that had \r\n
    #line endings before I added in the replace portions.  Now it doesn't seem
    #to have any problems...other than being slow.
    use = [parser.suite(source.replace('\r', '')).tolist()]
    
    #for line numbers, the parser module gacks...so we have the fast parser
    numbers = fast_parser(source, detectLineEndings(source), 1)
    numbers.reverse()
    
    out = []
    stk = []
    last = ''
    #line_no = 0
    names = {}
    ListType = type([])
    IntType = type(0)
    while use:
        #if we've gone up the tree parse tree enough to toss the current scope
        #out...toss it out.
        if stk and (stk[-1][2] > len(use)):
            prev = stk.pop()
            if stk:
                stk[-1][-1].append(prev)
            else:
                out.append(prev)
        cur = use.pop()
        while cur:
            obj = cur.pop(0)
            if type(obj) is ListType:
                use.append(cur)
                cur = obj
            elif type(obj) is IntType:
                if obj == 1: #token.NAME
                    if kw.get(cur[0], 1) and last:
                        while stk and (stk[-1][2] >= len(use)):
                            prev = stk.pop()
                            if stk:
                                stk[-1][-1].append(prev)
                            else:
                                out.append(prev)
                        nam = last+cur[0]
                        nl = nam.lower()
                        names[cur[0]] = None
                        last = ''

                        #the while and if make sure to use the use proper line
                        #numbers from fast_parser
                        while len(numbers) and (numbers[-1][0] != nam):cr = numbers.pop()
                            #print numbers[-1][1], line_no, nam, numbers[-1][0]
                        if not len(numbers): numbers.append(cr)
                        
                        stk.append([nam, (nl, numbers[-1][1]), len(use), []])
                        
                        if len(numbers)>1:cr = numbers.pop()
                            #print numbers[-1][1], line_no, nam, numbers[-1][0]
                    elif cd.get(cur[0], 0):
                        last = cur[0] + ' '
    while len(stk)>1:
        prev = stk.pop()
        stk[-1][-1].append(prev)
    out.extend(stk)
    return out, names.keys()

def leading(line):
    cur = 0
    while line[cur:cur+1] == ' ':
        cur += 1
    return cur

def fast_parser(source, line_ending, flat=0):
    lines = source.replace('\t', 8*' ').split(line_ending)
    out = []
    stk = []
    if flat: flattened = []
    names = {}
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
                        if flat: flattened.append((nam, line_no))
                        nl = nam.lower()
                        names[fn] = None
                        stk.append([nam, (nl, line_no), lead, []])
                        break
        #else non-function or non-class definition lines
    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat:
        return flattened
    return out, names.keys()

cf_heirarchy = fast_parser

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
        slow_parser(txt)
        tim();print 'done.'

    else:
        print 'usage:\n python parsers.py <source file>'
