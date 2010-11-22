#----------------------------- configuration.py ------------------------------
#----------------------- Settings for configuring PPE ------------------------
import os
import sys
from wxPython.stc import *

#--------- If I'm wrong on any of the line endings, please tell me. ----------
crlf = ["nt", "dos", "ce", "os2"]
lf = ["posix", "riscos", "java"]
cr = ["mac"]
fmt_mode = {"\r\n":wxSTC_EOL_CRLF,
              "\n":wxSTC_EOL_LF,
              "\r":wxSTC_EOL_CR}
if os.name in crlf: eol = "\r\n"
elif os.name in lf: eol = "\n"
elif os.name in cr: eol = "\r"
else:               eol = "\n"
eolmode = fmt_mode[eol]

runpath = os.path.split(sys.argv[0])[0]

stylefile = os.path.join(runpath, 'stc-styles.rc.cfg')

#light vert line just before this column number
#that is after this many characters
col_line = 78

#width of the left margin in pixels (I like mine big)
margin_width = 40

#for those collapseable source blocks (they rock)
collapse = 1
collapse_style = 0

#most python users use this...Stay away from tabs, they reduce file size,
#but are a bitch when it comes to formatting.
indent = 4
use_tabs = 0

#for open/save dialogs
wildcard = "All python files (*.py*)|*.py*|"\
           "C/C++ files (*.c*)|*.c*|"\
           "C/C++ headers (*.h)|*.h|"\
           "XML files (*.xml)|*.xml|"\
           "HTML files (*.htm*)|*.htm*|"\
           "SHTML files (*.shtm*)|*.shtm*|"\
           "All files (*.*)|*.*"

#for style mappings from extensions
extns = {'py' : 'python',
        'pyw' : 'python',
          'c' : 'cpp',
         'cc' : 'cpp',
        'cpp' : 'cpp',
        'c++' : 'cpp',
          'h' : 'cpp',
        'htm' : 'html',
       'html' : 'html',
       'shtm' : 'html',
      'shtml' : 'html',
        'xml' : 'xml'}

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
#------------------------- load bookmarked hot-keys --------------------------
try:
    from pathmarks import *
except:
    paths = {}
