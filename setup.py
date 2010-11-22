# setup.py
# to make a binary for windows from source...
# 1. download and install the py2exe utility from:
#      http://starship.python.net/crew/theller/py2exe/
# 2. run the following command:
#      python setup.py py2exe

from distutils.core import setup
import pype
try:
    import py2exe
except:
    pass
import glob
import os

nam = "PyPE-win32"
if pype.VS[-1] == 'u':
    nam += '-unicode'

def glob_(path, extns):
    x = []
    for i in extns:
        x.extend(glob.glob(os.path.join(path, i)))
    return x
    
samples = os.path.join('macros', 'samples')

setup(name=nam,
      version=pype.VERSION_,
      windows=[{"script": "pype.py",
                "icon_resources": [(1, os.path.join("icons", "pype.ico"))]}],
      data_files=[('', glob.glob('*.txt')+\
                   ['stc-styles.rc.cfg', 'readme.html']),
                   ('icons', glob.glob(os.path.join('icons', '*.*'))),
                   #('macros', glob.glob(os.path.join('macros', '*.py'))),
                   (samples, glob_(samples, ('*.txt', '*.py')))],
      options = {"py2exe": {"packages": ["encodings"],
                            "compressed": 1}}
)
