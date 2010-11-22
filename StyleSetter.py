
import sys
import wx
import wx.stc

import configuration #for unrepr

cn = 'Courier New'
fs = 10
if 'darwin' == sys.platform:
    fs = 13

def update_faces():
    global faces
    faces = {'times': cn, 'mono' : cn, 'helv' : cn, 'other': cn, 'lucd': cn,
             'size' : fs, 'size2': fs, 'lnsize': fs, "forecol":"#000000",
             "backcol": "#ffffff"}

update_faces()

def partition(st, sep):
    if sep not in st:
        return st, '', ''
    x = st.find(sep)
    return st[:x], sep, st[x+len(sep):]

def rpartition(st, sep):
    if sep not in st:
        return '', '', st
    x = st.rfind(sep)
    return st[:x], sep, st[x+len(sep):]

_default = {34:'fore:#0000FF,back:#FFFF88,bold', 35:'fore:#FF0000,back:#FFFF88,bold'}

def get_style(stylefile, language, _faces, profile=''):
    #gets the main styling information for [style.<language>[.profile]]
    found1 = 0
    dct = {}
    if profile == 'default':
        dct.update(_default)
    line_starts1 = 'style.%s.'%language
    line_starts2 = 'setting.%s.'%language
    if profile:
        profile = '.' + profile
    looking_for = '[style.%s%s]'%(language, profile)
    for line in open(stylefile):
        if line.strip() == looking_for:
            found1 = 1
        elif found1 and (line.startswith(line_starts1) or line.startswith(line_starts2)):
            left, _, right = partition(line, '=')
            if not _:
                continue
            toss, _, num = rpartition(left, '.')
            if toss and _ and num:
                try:
                    num = int(num, 10)
                except:
                    continue
            dct[num] = right.strip()%_faces
        elif found1 and not line.strip():
            pass
        elif found1:
            break
    return dct

def get_extra(stylefile, language):
    found2 = 0
    dct = {}
    looking_for = '[%s]'%language
    for line in open(stylefile):
        if line.strip() == looking_for:
            found2 = 1
        elif found2 and not line.startswith('[') and line.strip():
            left, _, right = partition(line, '=')
            if left and _:
                dct[left] = right.strip()
        elif found2 and not line.strip():
            pass
        elif found2:
            break
    return dct

def get_faces(stylefile):
    if 'win32' in sys.platform:
        start = 'common.defs.msw'
    else:
        start = 'common.defs.gtk'
    
    x = {}
    for line in open(stylefile):
        if line.startswith(start):
            try:
                x = configuration.unrepr(line[len(start):].lstrip(' ='))
            except:
                pass
    return x

def initSTC(stc, stylefile, language, custom=''):
    #get the styling information
    _faces = dict(faces)
    _faces.update(get_faces(stylefile))
    
    styles = get_style(stylefile, language, _faces, 'default')
    styles.update(get_style(stylefile, language, _faces, custom))
    
    ## print "got styling information:", [i.strip() for i in lines1]
    
    #get any extra bits

    extra = get_extra(stylefile, language)
    ## import pprint
    ## pprint.pprint(extra)
    #get the actual lexer
    lexer = wx.stc.STC_LEX_NULL
    if 'lexer' in extra:
        lex = extra['lexer']
        if lex.startswith('wx'):
            lex = lex[2:]
            lex.lstrip('.')
            if hasattr(wx.stc, lex):
                lexer = getattr(wx.stc, lex)
    
    _base = 'fore:%(forecol)s,back:%(backcol)s,face:%(mono)s,size:%(size)d'%_faces
    stc.StyleResetDefault()
    stc.ClearDocumentStyle()
    stc.SetLexer(lexer)
    stc.SetKeyWords(0, extra.get('keywords', ''))
    stc.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, _base)
    stc.StyleClearAll()
    
    for num, style in styles.iteritems():
        if num >= 0:
            stc.StyleSetSpec(num, style)
        elif num == -1:
            setSelectionColour(stc, style)
        elif num == -2:
            setCursorColour(stc, style)
        elif num == -3:
            setEdgeColour(stc, style)
    
    #borrowed from STCStyleEditor
    bkCol = None
    if 0 in styles: prop = styles[0]
    else: prop = _base
    names, vals = parseProp(prop)
    if 'back' in names:
        bkCol = strToCol(vals['back'])
    if bkCol is None:
        bkCol = '#ffffff'
    stc.SetBackgroundColour(bkCol)
        
    stc.Colourise(0, stc.GetTextLength())

#from STCStyleEditor.py

def strToCol(strCol):
    assert len(strCol) == 7 and strCol[0] == '#', 'Not a valid colour string'
    return wx.Colour(int(strCol[1:3], 16),
                     int(strCol[3:5], 16),
                     int(strCol[5:7], 16))

def setSelectionColour(stc, style):
    names, values = parseProp(style)
    if 'fore' in names:
        stc.SetSelForeground(True, strToCol(values['fore']))
    if 'back' in names:
        stc.SetSelBackground(True, strToCol(values['back']))

def setCursorColour(stc, style):
    names, values = parseProp(style)
    if 'fore' in names:
        stc.SetCaretForeground(strToCol(values['fore']))

def setEdgeColour(stc, style):
    names, values = parseProp(style)
    if 'fore' in names:
        stc.SetEdgeColour(strToCol(values['fore']))

def parseProp(prop):
    items = prop.split(',')
    names = []
    values = {}
    for item in items:
        nameVal = item.split(':')
        names.append(nameVal[0].strip())
        if len(nameVal) == 1:
            values[nameVal[0]] = ''
        else:
            values[nameVal[0]] = nameVal[1].strip()
    return names, values

