"""Simple code to extract class & function docstrings from a module.

This code is used as an example in the library reference manual in the
section on using the parser module.  Refer to the manual for a thorough
discussion of the operation of this code.

The code has been extended by Stephen Davies for the Synopsis project. It now
also recognises parameter names and values, and baseclasses. Names are now
returned in order also.

July 25, 2006
Adapted from Synopsis package, which is LGPL licensed.
"""

import compiler
import parser
import re
import symbol
import sys
import token

line_end = ((token.NEWLINE, ''), (token.INDENT, ''), (token.DEDENT, ''))

def format(tree, depth=-1):
    """Format the given tree up to the given depth.
    Numbers are replaced with their symbol or token names."""
    if isinstance(tree, int):
        try:
            return symbol.sym_name[tree]
        except KeyError:
            try:
                return token.tok_name[tree]
            except KeyError:
                return tree
    if type(tree) != tuple:
        return tree
    if depth == 0: return '...'
    ret = [format(tree[0])]
    for branch in tree[1:]:
        ret.append(format(branch, depth-1))
    return tuple(ret)

def stringify(tree):
    """Convert the given tree to a string"""
    if isinstance(tree, int): return ''
    if not isinstance(tree, tuple):
        return str(tree)
    strs = []
    for elem in tree:
        strs.append(stringify(elem))
    return ''.join(strs)

def get_docs(source):
    return ModuleInfo(parser.suite(source).totuple(), '')

def parse(content):
    stk = [get_docs(content)]
    names_ = []
    out = []
    outt = []
    docstring = {}
    p = 0
    lineno = 1
    while stk:
        cur = stk.pop()
        if cur is None:
            _ = outt.pop()
            __ = names_.pop()
            if len(outt) == 0:
                out.append(_)
            continue
        elif isinstance(cur, list):
            if len(cur) >= 1:
                stk.append(cur)
                stk.append(cur.pop())
            continue
            
        elif isinstance(cur, ModuleInfo):
            x = ''
        elif isinstance(cur, ClassInfo):
            _name = cur.get_name()
            x = 'class ' + _name
            gbm = cur.get_base_names()
            if gbm:
                x += '(%s)'%(', '.join(gbm))
                
        elif isinstance(cur, FunctionInfo):
            _name = cur.get_name()
            x = 'def %s(%s)'%(_name,
                ', '.join([(i, '%s=%s'%(i,j))[bool(j)]
                            for i,j in zip(cur.get_params(),
                                           cur.get_param_defaults())]))
        else:
            print "huh?"
            continue
        
        if x:
            z = 'def'
            if isinstance(cur, ClassInfo):
                z = 'class'
            g = re.compile("(?:^|\s)%s\s+%s(?:[:\s\(\\\\]|$)"%(z, _name),
                           re.MULTILINE).search(content, p)
            if g:
                #we found the definition
                h = g.group()
                s = g.start()
                s += len(h) - len(h.lstrip())
                lineno += content.count('\n', p, s)
                p = g.end()
            y = (x, (_name.lower(), lineno, _name), len(outt)*4, [])
            if len(outt):
                outt[-1][-1].append(y)
            
            
            doc = cur.get_docstring()
            _ = '.'.join(names_)
            if _:
                _ += '.'
            doc = ('%s%s\n%s'%(_, x.split(None, 1)[-1], doc)).rstrip()
            docstring.setdefault(_name, []).append(doc)
            if _name in ('__init__', '__new__') and outt:
                docstring.setdefault(outt[-1][1][2], []).append(doc)
            
            names_.append(_name)
            outt.append(y)        
            stk.append(None)
        
        names = [j for i,j in cur.get_names_and_info()]
        names.reverse()
        stk.append(names)
    
    if outt:
        out.append(outt[0])
    
    return out, docstring

class SuiteInfoBase:
    if 1:
        _docstring = ''
        _name = ''

    def __init__(self, tree = None, env={}):
        self._env = {} ; self._env.update(env)
        self._names = []
        self._imports = []
        ## self._class_info = {}
        ## self._class_names = []
        ## self._function_info = {}
        ## self._function_names = []
        if tree:
            self._extract_info(tree)
    
    def _extract_info(self, tree):
        # extract docstring
        if len(tree) == 2:
            found, vars = match(DOCSTRING_STMT_PATTERN[1], tree[1])
        else:
            try:
                found, vars = match(DOCSTRING_STMT_PATTERN, tree[3])
            except:
                ## import pprint
                ## pprint.pprint(tree)
                raise
        if found:
            self._docstring = eval(vars['docstring'])
        # discover inner definitions
        for node in tree[1:]:
            found, vars = match(COMPOUND_STMT_PATTERN, node)
            if found:
                cstmt = vars['compound']
                if cstmt[0] == symbol.funcdef:
                    name = cstmt[2][1]
                    self._names.append((name, FunctionInfo(cstmt, env=self._env)))
                elif cstmt[0] == symbol.classdef:
                    name = cstmt[2][1]
                    self._names.append((name, ClassInfo(cstmt, env=self._env)))
    def get_docstring(self):
        return self._docstring

    def get_names_and_info(self):
        return self._names
    
    def get_name(self):
        return self._name

class FunctionInfo(SuiteInfoBase):
    def __init__(self, tree = None, env={}):
        index = 3
        self._name = tree[index-1][1]
        if self._name == 'def':
            self._name = tree[index][1]
            index += 1
        SuiteInfoBase.__init__(self, tree and tree[-1] or None, env)
        self._params = []
        self._param_defaults = []
        if tree[index][0] == symbol.parameters:
            if tree[index][2][0] == symbol.varargslist:
                args = list(tree[index][2][1:])
                while args:
                    if args[0][0] == token.COMMA:
                        pass
                    elif args[0][0] == symbol.fpdef:
                        self._params.append(stringify(args[0]))
                        self._param_defaults.append('')
                    elif args[0][0] == token.EQUAL:
                        del args[0]
                        self._param_defaults[-1] = stringify(args[0])
                    elif args[0][0] == token.DOUBLESTAR:
                        del args[0]
                        self._params.append('**'+stringify(args[0]))
                        self._param_defaults.append('')
                    elif args[0][0] == token.STAR:
                        del args[0]
                        self._params.append('*'+stringify(args[0]))
                        self._param_defaults.append('')
                    else:
                        print "Unknown symbol:",args[0]
                    del args[0]
    
    def get_params(self): return self._params
    def get_param_defaults(self): return self._param_defaults


class ClassInfo(SuiteInfoBase):
    def __init__(self, tree = None, env={}):
        self._name = tree[2][1]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None, env)
        self._bases = []
        if tree[4][0] == symbol.testlist:
            for test in tree[4][1:]:
                found, vars = match(TEST_NAME_PATTERN, test)
                if found and vars.has_key('power'):
                    power = vars['power']
                    if power[0] != symbol.power: continue
                    atom = power[1]
                    if atom[0] != symbol.atom: continue
                    if atom[1][0] != token.NAME: continue
                    name = [atom[1][1]]
                    for trailer in power[2:]:
                        if trailer[2][0] == token.NAME: name.append(trailer[2][1])
                    if self._env.has_key(name[0]):
                        name = self._env[name[0]] + name[1:]
                        self._bases.append(name)
                        #print "BASE:",name
                    else:
                        #print "BASE:",name[0]
                        self._bases.append(name[0])
        else:
            pass

    def get_base_names(self):
        return self._bases

class ModuleInfo(SuiteInfoBase):
    def __init__(self, tree = None, name = "<string>"):
        self._name = name
        SuiteInfoBase.__init__(self, tree)
        if tree:
            found, vars = match(DOCSTRING_STMT_PATTERN, tree[1])
            if found:
                self._docstring = eval(vars["docstring"])

def match(pattern, data, vars=None):
    """Match `data' to `pattern', with variable extraction.

    pattern
        Pattern to match against, possibly containing variables.

    data
        Data to be checked and against which variables are extracted.

    vars
        Dictionary of variables which have already been found.  If not
        provided, an empty dictionary is created.

    The `pattern' value may contain variables of the form ['varname'] which
    are allowed to match anything.  The value that is matched is returned as
    part of a dictionary which maps 'varname' to the matched value.  'varname'
    is not required to be a string object, but using strings makes patterns
    and the code which uses them more readable.

    This function returns two values: a boolean indicating whether a match
    was found and a dictionary mapping variable names to their associated
    values.
    """
    if vars is None:
        vars = {}
    if type(pattern) is list:       # 'variables' are ['varname']
        vars[pattern[0]] = data
        return 1, vars
    if type(pattern) is not tuple:
        return (pattern == data), vars
    if len(data) != len(pattern):
        return 0, vars
    for pattern, data in map(None, pattern, data):
        same, vars = match(pattern, data, vars)
        if not same:
            break
    return same, vars

def dmatch(pattern, data, vars=None):
    """Debugging match """
    if vars is None:
        vars = {}
    if type(pattern) is list:       # 'variables' are ['varname']
        vars[pattern[0]] = data
        print "dmatch: pattern is list,",pattern[0],"=",data
        return 1, vars
    if type(pattern) is not tuple:
        print "dmatch: pattern is not tuple, pattern =",format(pattern)," data =",format(data)
        return (pattern == data), vars
    if len(data) != len(pattern):
        print "dmatch: bad length. data=",format(data,2)," pattern=",format(pattern,1)
        return 0, vars
    for pattern, data in map(None, pattern, data):
        same, vars = dmatch(pattern, data, vars)
        if not same:
            print "dmatch: not same"
            break
        print "dmatch: same so far"
    print "dmatch: returning",same,vars
    return same, vars

#  This pattern identifies compound statements, allowing them to be readily
#  differentiated from simple statements.
#
COMPOUND_STMT_PATTERN = (
    symbol.stmt,
    (symbol.compound_stmt, ['compound'])
    )


#  This pattern will match a 'stmt' node which *might* represent a docstring;
#  docstrings require that the statement which provides the docstring be the
#  first statement in the class or function, which this pattern does not check.
#
DOCSTRING_STMT_PATTERN = (
    symbol.stmt,
    (symbol.simple_stmt,
     (symbol.small_stmt,
      (symbol.expr_stmt,
       (symbol.testlist,
        (symbol.test,
         (symbol.and_test,
          (symbol.not_test,
           (symbol.comparison,
            (symbol.expr,
             (symbol.xor_expr,
              (symbol.and_expr,
               (symbol.shift_expr,
                (symbol.arith_expr,
                 (symbol.term,
                  (symbol.factor,
                   (symbol.power,
                    (symbol.atom,
                     (token.STRING, ['docstring'])
                     )))))))))))))))),
     (token.NEWLINE, '')
     ))

#  This pattern will match a 'test' node which is a base class
#
TEST_NAME_PATTERN = (
        symbol.test,
         (symbol.and_test,
          (symbol.not_test,
           (symbol.comparison,
            (symbol.expr,
             (symbol.xor_expr,
              (symbol.and_expr,
               (symbol.shift_expr,
                (symbol.arith_expr,
                 (symbol.term,
                  (symbol.factor,
                    ['power']
                  ))))))))))
     )

# This pattern will match an import statement
# import_spec is either:
#   NAME:import, dotted_name
# or:
#   NAME:from, dotted_name, NAME:import, NAME [, COMMA, NAME]*
# hence you must process it manually (second form has variable length)
IMPORT_STMT_PATTERN = (
      symbol.stmt, (
        symbol.simple_stmt, (
          symbol.small_stmt,
            (symbol.import_stmt, ['import_spec'])
        ), (
          token.NEWLINE, ''
        )
      )
)

#------------------------------- new parser :) -------------------------------
USE_AST = False
if sys.version >= '2.5':
    # try to use the new ast module, it's faster than compiler.ast :)
    USE_AST = True
    import _ast

# these functions are inspired/copied from their equivalents in Python
# 2.6's high-level ast module
fields = lambda node: ((field, getattr(node, field, None)) for field in node._fields)

def transform(node):
    # transform the targets in for/with clauses to assignment nodes
    if isinstance(node, _ast.For):
        a = _ast.Assign()
        a.targets = [node.target]
        yield a
    elif isinstance(node, _ast.With) and node.optional_vars:
        a = _ast.Assign()
        a.targets = [node.optional_vars]
        yield a
    yield node

def _child_nodes(node):
    ast = _ast.AST
    if not node._fields:
        return
    for name, field in fields(node):
        if isinstance(field, ast):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, ast):
                    yield item

def child_nodes(node):
    trans = transform
    for i in _child_nodes(node):
        for j in trans(i):
            yield j

def cleandoc(doc):
    """Clean up indentation from docstrings.

    Any whitespace that can be uniformly removed from the second line
    onwards is removed."""
    # borrowed and modified from Python trunk source
    try:
        lines = doc.expandtabs().split('\n')
    except UnicodeError:
        return None
    else:
        # Find minimum indentation of any non-blank lines after first line.
        margin = sys.maxint
        for line in lines[1:]:
            content = len(line.lstrip())
            if content:
                indent = len(line) - content
                margin = min(margin, indent)
        # Remove indentation.
        if lines:
            lines[0] = lines[0].lstrip()
        if margin < sys.maxint:
            for i in xrange(1, len(lines)):
                lines[i] = lines[i][margin:]
        # Remove any trailing or leading blank lines.
        return '\n'.join(lines).strip('\n')

def get_docstring(node, clean=True):
    if not isinstance(node, (_ast.FunctionDef, _ast.ClassDef, _ast.Module)):
        raise TypeError("%r can't have docstrings" % node.__class__.__name__)
    if node.body and isinstance(node.body[0], _ast.Expr) and \
       isinstance(node.body[0].value, _ast.Str):
        return cleandoc(node.body[0].value.s)

def translate_old_to_new(ucky_old_stuff, docs, last_line, depth=1, parent=''):
    out = []
    if depth == 1:
        # we probably want to fix this at the end...
        out.append(Info(-1, '', '', 0, -1, (), None, None, last_line))
    maxline = 0
    luos = len(ucky_old_stuff)-1
    for posn, node in enumerate(ucky_old_stuff):
        defn, (name_lower, lineno, name), indent, children = node
        # we do short and long after the fact :)
        dl = parent
        if parent:
            dl += '.'
        dl += name
        nn = ' '+name
        if nn not in defn:
            doc_lookup = dl + defn.split(name, 1)[1]
        else:
            doc_lookup = dl + defn.split(' '+name, 1)[1]
        doc = None
        if doc_lookup in docs:
            if docs[doc_lookup]:
                doc = docs[doc_lookup].pop(0)
                if '\n' in doc:
                    doc = doc.split('\n', 1)[1]
                else:
                    doc = None
        lastl = last_line
        if posn < luos:
            lastl = ucky_old_stuff[posn+1][1][1]
        out.append(Info(lineno, name, defn, depth, indent, (), None, doc, lastl-lineno))
        if children:
            out.extend(translate_old_to_new(children, docs, lastl, depth+1, dl))
    out.sort()
    if depth == 1:
        names = set()
        for entry in out:
            if entry.lineno < 0:
                continue
            names.add(entry.name)
            entry.search_list = out[0]
        out[0].search_list = ()
        out[0].locals = names and sorted(names) or ()
        return out, _fixup_extra(out)
    return out

_new_scope = (compiler.ast.Function, compiler.ast.Class)
_new_scope_ast = (_ast.FunctionDef, _ast.ClassDef)

class InfoObj(object):
    def __init__(self, *args):
        if len(args) < self.required:
            raise ValueError("needed %i arguments, got %i"%(len(self.__slots__), len(args)))
        for n, v in zip(self.__slots__, args):
            setattr(self, n, v)
        for i in xrange(len(args), len(self.__slots__)):
            setattr(self, self.__slots__[i], '')
        if len(self.__slots__) > 4:
            if not self.olines:
                self.olines = 0
    def __getitem__(self, index):
        ## if index != 0:
            ## print "index", index, "key", self.__slots__[index]
        return getattr(self, self.__slots__[index])
    def __setitem__(self, index, value):
        setattr(self, self.__slots__[index], value)
    def __repr__(self):
        return str([(k,getattr(self, k)) for k in self.__slots__ if k not in ('locals', 'search_list', 'lex_parent')])
    def __cmp__(self, other):
        if other is None:
            return 1
        if other is self:
            return 0
        return cmp(self[0], other[0])

class Info(InfoObj):
    __slots__ = 'lineno name defn depth indent locals search_list doc lines short long olines lex_parent fileinfo'.split()
    required = 9

class Import(InfoObj):
    __slots__ = 'lineno module_import local_name'.split()
    required = 3

def postorder(node, depth):
    if USE_AST:
        for _ in postorder_ast(node, depth):
            yield _
        return
    new_scope = _new_scope
    rev = reversed
    get = getattr
    isi = isinstance
    nod = compiler.ast.Node
    lam = (compiler.ast.GenExpr, compiler.ast.Lambda)
    if sys.version >= '2.6':
        lam = (compiler.ast.ListComp,) + lam
    
    stk = [(node, depth)]
    while stk:
        node, depth = stk.pop()
        if get(node, 'visited', 0):
            yield node, depth
            continue
        node.visited = 1
        depth += isi(node, new_scope)
        ch = node.getChildNodes()
        if ch and not isi(node, lam):
            stk.append((node, depth))
            stk.extend((chi, depth) for chi in rev(ch) if isi(chi, nod))
        else:
            yield node, depth

def postorder_ast(node, depth):
    new_scope = _new_scope_ast
    nodes = child_nodes
    has = hasattr
    rev = reversed
    get = getattr
    isi = isinstance
    nod = _ast.AST
    lam = (_ast.GeneratorExp, _ast.Lambda)
    if sys.version >= '3.0':
        lam = (_ast.ListComp,) + lam
    
    _id = id

    visited = set()
    stk = [(node, depth)]
    while stk:
        node, depth = stk.pop()
        if _id(node) in visited:
            if isi(node, new_scope) and has(node, 'lineno') and has(node, 'decorators'):
                node.lineno += len(node.decorators)
            yield node, depth
            continue
        visited.add(_id(node))
        depth += isi(node, new_scope)
        ch = list(nodes(node))
        if ch and not isi(node, lam):
            stk.append((node, depth))
            stk.extend((chi, depth) for chi in rev(ch) if isi(chi, nod))
        else:
            if isi(node, new_scope) and has(node, 'lineno') and has(node, 'decorators'):
                node.lineno += len(node.decorators)
            yield node, depth

def iter_tree(entries, include_labels=True):
    stk = []
    for data in entries:
        if data.depth <= 0:
            continue
        while stk and data.depth <= stk[-1].depth:
            _ = stk.pop()
        stk.append(data)
        if data[2][:2] == '--' and not include_labels:
            stk.pop()
            continue
        yield stk

def _fixup_extra(entries):
    docs = {}
    tcounts = {}
    stk_seq = [list(stk) for stk in iter_tree(entries)]
    for stk in reversed(stk_seq):
        ## print stk
        last = stk[-1]
        last.olines = last.lines
        if len(stk) > 1:
            last.lex_parent = stk[-2]
        else:
            last.lex_parent = entries[0]
        
        # Let's get some good names...
        short = '.'.join(i.name for i in stk)
        last.short = last.defn.replace(last.name, short, 1)
        last.long = ': '.join(i.defn for i in stk)
        
        # We want to fix line count information
        last.lines -= tcounts.get(id(last), 0)
        for i in stk[:-1]:
            tcounts[id(i)] = tcounts.get(id(i), 0) + last.lines
        
        # We are going to add a reference to a parent scope, if available.
        # We've already got the imports for each function.
        if last.search_list is None:
            for si in reversed(stk):
                if si is last:
                    continue
                if not si.defn.startswith('class '):
                    last.search_list = si
                    break
            else:
                last.search_list = entries[0]
        
        # Generate documentation
        if last.name:
            doc = last.doc and '\n'+last.doc or ''
            docs.setdefault(last.name, []).append('%s%s'%(last.short, doc))
            if last.name in ('__init__', '__new__') and short.count('.') > 0:
                docs.setdefault(short.rsplit('.', 2)[-2], []).append(docs[last.name][-1])

    return docs

def _parse(source):
    if USE_AST:
        return _parse_ast(source)
    lines_to_positions = {0:0}
    for line, match in enumerate(re.finditer('\n', source)):
        lines_to_positions[line+1] = match.end()
    lines_to_positions[len(lines_to_positions)] = len(source)

    # cache these references
    isi = isinstance
    new_scope = _new_scope
    fcn = compiler.ast.Function
    ass = compiler.ast.AssName
    assa = compiler.ast.AssAttr
    name = compiler.ast.Name
    fro = compiler.ast.From
    imp = compiler.ast.Import
    mod = compiler.ast.Module
    self_names = set(('self', 'cls', 'klass', 'class_', '_class'))

    # list of Info() objects
    out = []
    # imports are a list of (line_no, module_import, local_name)
    # indent is the indentation of the function/class, tabs = 8 spaces
    
    tree = compiler.parse(source)
    known = {}
    attrs = {}
    last = {}

    for node, depth in postorder(tree, 0):
        # this last dictionary is to allow us to pull the body of an entire
        # function if necessary for discovering it's arg list
        last[depth] = max(node.lineno, last.get(depth, 0))
        if depth not in known:
            known[depth] = set()
        if depth not in attrs:
            attrs[depth] = set()
        
        if isi(node, new_scope):
            # pull the locals from the current depth, and toss it in the out
            # bucket; also add the function name to the depth-1 listing
            names = known.pop(depth)
            node.lastlineno = last.pop(depth)
            last[depth-1] = max(node.lastlineno, last.get(depth-1, 0))
            if isinstance(node, fcn):
                names.update(node.argnames)
                an = node.argnames[:]
                if node.kwargs:
                    an[-1] = '**' + an[-1]
                    if node.varargs:
                        an[-2] = '*' + an[-2]
                elif node.varargs:
                    an[-1] = '*' + an[-1]
                elif node.defaults:
                    an = [get_defaults(node, source, lines_to_positions)]
                for i,j in enumerate(an):
                    if type(j) is tuple:
                        # tuple unpacking in argument lists
                        an[i] = fix_tuples(j)
                signature = 'def %s(%s)'%(node.name, ', '.join(an))
            else:
                for i in xrange(depth, max(attrs)+1):
                    names.update(attrs.pop(i, ()))
                if not node.bases:
                    signature = 'class %s'%(node.name,)
                else:
                    signature = 'class %s(%s)'%(node.name, get_defaults(node, source, lines_to_positions, 0))
            startline = source[lines_to_positions[node.lineno-1]:lines_to_positions[node.lineno]].replace('\t', '        ')
            indent = len(startline) - len(startline.lstrip())
            out.append(Info(node.lineno, node.name, signature, depth, indent, sorted(names), None, node.doc, node.lastlineno-node.lineno+1, None, None))
            known.setdefault(depth-1, set()).add(node.name)
        
        elif isi(node, ass):
            # it's an assignment, toss it into the locals list
            known[depth].add(node.name)

        elif isi(node, assa):
            # it's an attribute assignment, toss it into the attrs list
            if isinstance(node.expr, name) and node.expr.name in self_names:
                attrs[depth].add(node.attrname)
        
        elif isi(node, fro):
            lead = node.level*'.' + node.modname
            for oname, dname in node.names:
                if oname != '*':
                    known[depth].add(dname or oname)
                    known[depth].add(Import(node.lineno, lead + '.' + oname, dname or oname))
                else:
                    known[depth].add(Import(node.lineno, lead, oname))
        
        elif isi(node, imp):
            for oname, dname in node.names:
                if dname is None or oname == dname:
                    known[depth].add(oname.split('.')[0])
                    known[depth].add(Import(node.lineno, oname, oname))
                    while '.' in oname:
                        oname = oname.rsplit('.', 1)[0]
                        known[depth].add(Import(node.lineno, oname, oname))
                else:
                    known[depth].add(dname)
                    known[depth].add(Import(node.lineno, oname, dname))
        
        elif isi(node, mod):
            # don't really need the documentation here, but eh?
            names = known.pop(depth)
            for i in xrange(depth-1, max(attrs)+1):
                names.update(attrs.pop(i, ()))
            ## print "have module at depth", depth, "with names", names
            out.append(Info(-1, '', '', depth, -1, sorted(names), None, node.doc, last[depth] - (node.lineno or 1) + 1))
    
    out.sort()
    docs = _fixup_extra(out)
    return out, docs

def _parse_ast(source):
    lines_to_positions = {0:0}
    for line, match in enumerate(re.finditer('\n', source)):
        lines_to_positions[line+1] = match.end()
    lines_to_positions[len(lines_to_positions)] = len(source)

    # cache these references
    isi = isinstance
    new_scope = _new_scope_ast
    fcn = _ast.FunctionDef
    ass = _ast.Assign
    att = _ast.Attribute
    name = _ast.Name
    tup = (_ast.Tuple, _ast.List)
    fro = _ast.ImportFrom
    imp = _ast.Import
    mod = _ast.Module
    self_names = set(('self', 'cls', 'klass', 'class_', '_class'))

    # list of Info() objects
    out = []
    # imports are a list of (line_no, module_import, local_name)
    # indent is the indentation of the function/class, tabs = 8 spaces
    
    tree = compile(source, "<unknown>", "exec", _ast.PyCF_ONLY_AST)
    known = {}
    attrs = {}
    last = {}

    for node, depth in postorder_ast(tree, 0):
        # this last dictionary is to allow us to pull the body of an entire
        # function if necessary for discovering it's arg list
        last[depth] = max(getattr(node, 'lineno', 0), last.get(depth, 0))
        if depth not in known:
            known[depth] = set()
        if depth not in attrs:
            attrs[depth] = set()
        
        if isi(node, new_scope):
            # pull the locals from the current depth, and toss it in the out
            # bucket; also add the function name to the depth-1 listing
            names = known.pop(depth)
            node.lastlineno = last.pop(depth)
            last[depth-1] = max(node.lastlineno, last.get(depth-1, 0))
            if isi(node, fcn):
                an = [get_defaults(node, source, lines_to_positions)]
                _a = node.args.args + [node.args.vararg, node.args.kwarg]
                for _name in _a:
                    if not _name:
                        pass
                    elif isi(_name, tuple):
                        _a.extend(_name)
                    elif isi(_name, _ast.Name):
                        names.add(_name.id)
                    elif isi(_name, (str, unicode)):
                        names.add(_name)
                signature = 'def %s(%s)'%(node.name, ', '.join(an))
            else:
                for i in xrange(depth, max(attrs)+1):
                    names.update(attrs.pop(i, ()))
                if not node.bases:
                    signature = 'class %s'%(node.name,)
                else:
                    signature = 'class %s(%s)'%(node.name, get_defaults(node, source, lines_to_positions, 0))
            startline = source[lines_to_positions[node.lineno-1]:lines_to_positions[node.lineno]].replace('\t', '        ')
            indent = len(startline) - len(startline.lstrip())
            out.append(Info(node.lineno, node.name, signature, depth, indent, sorted(names), None, get_docstring(node), node.lastlineno-node.lineno+1, None, None))
            known.setdefault(depth-1, set()).add(node.name)
        
        elif isi(node, ass):
            # it's an assignment, toss it into the locals list
            _a = node.targets[:]
            for _name in _a:
                if isi(_name, name):
                    known[depth].add(_name.id)
                elif isi(_name, tup):
                    _a.extend(_name.elts)
                elif isi(_name, att):
                    if isi(_name.value, name) and _name.value.id in self_names:
                        attrs[depth].add(_name.attr)

        elif isi(node, fro):
            lead = node.level*'.' + node.module
            for _name in node.names:
                oname, dname = _name.name, _name.asname
                if oname != '*':
                    known[depth].add(dname or oname)
                    known[depth].add(Import(node.lineno, lead + '.' + oname, dname or oname))
                else:
                    known[depth].add(Import(node.lineno, lead, oname))
                
        
        elif isi(node, imp):
            for _name in node.names:
                oname, dname = _name.name, _name.asname
                if dname is None or oname == dname:
                    known[depth].add(oname.split('.')[0])
                    known[depth].add(Import(node.lineno, oname, oname))
                    while '.' in oname:
                        oname = oname.rsplit('.', 1)[0]
                        known[depth].add(Import(node.lineno, oname, oname))
                else:
                    known[depth].add(dname)
                    known[depth].add(Import(node.lineno, oname, dname))
        
        elif isi(node, mod):
            # don't really need the documentation here, but eh?
            names = known.pop(depth)
            for i in xrange(depth-1, max(attrs)+1):
                names.update(attrs.pop(i, ()))
            out.append(Info(-1, '', '', depth, -1, sorted(names), None, get_docstring(node), last[depth]))
    
    out.sort()
    docs = _fixup_extra(out)
    return out, {}


def fix_tuples(x):
    if type(x) is not tuple:
        return x
    return '(' + ', '.join(map(fix_tuples, x)) + ')'

def _flatten(data):
    rev = reversed
    tup = tuple
    isi = isinstance

    stk = list(rev(data))
    while stk:
        item = stk.pop()
        if isi(item, tup):
            stk.extend(rev(item))
        else:
            yield item

def _get_tree(source, pattern):
    isi = isinstance
    bas = basestring
    for i in recmatch(parser.suite(source).totuple(), pattern):
        return [i for i in _flatten(i) if isi(i, bas)]
    return []

def get_defaults(fnode, source, lines, fcn=1):
    pattern = (CLASS_BASE_PATTERN, FCN_ARG_PATTERN)[fcn]
    start = lines[fnode.lineno-1]
    fend = lines[fnode.lineno]
    try:
        fc = fnode.code
        while isinstance(fc, compiler.ast.Stmt):
            fc = fc.nodes
        fend = lines[fc[0].lineno]
    except:
        fc = fnode.body
        fend = lines[fc[0].lineno-1]
    end = lines[fnode.lastlineno]
    try:
        # We'll try the fast version that only visits the function
        # signature...
        # This will fail if the first non-blank line of a function is a
        # comment.
        cur = _get_tree(source[start:fend].strip() + ' pass\n', pattern)
    except:
        # otherwise we'll parse the entire function
        cur = _get_tree(source[start:end].strip(), pattern)
    return ''.join(cur).replace(',', ', ')

def recmatch(data, pattern):
    stk = [(data, pattern, 1)]
    while stk:
        data, pattern, first = stk.pop()
        if type(data) == type(pattern) == tuple:
            # look for a match
            if first:
                stk.extend((data[i], pattern, 1) for i in xrange(len(data)-1, 0, -1))
            if data[0] == pattern[0]:
                if pattern[1] is None:
                    yield data
                else:
                    stk.extend((data[i], pattern[1], 0) for i in xrange(len(data)-1, 0, -1))

FCN_ARG_PATTERN = (
  symbol.stmt, (
    symbol.compound_stmt, (
      symbol.funcdef, (
        symbol.parameters, (
          symbol.varargslist, None
        )
      )
    )
  )
)

CLASS_BASE_PATTERN = (
  symbol.stmt, (
    symbol.compound_stmt, (
      symbol.classdef, (
        symbol.testlist, None
      )
    )
  )
)


#
#  end of file
