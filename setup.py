# setup.py
# to make a binary for windows from source...
# 1. download and install the py2exe utility from:
#      http://starship.python.net/crew/theller/py2exe/
# 2. run the following command:
#      python setup.py py2exe

from distutils.core import setup
try:
    import py2exe
except:
    pass
import pype
import glob
import os

nam = "PyPE-win32"
if pype.VS[-1] == 'u':
    nam += '-unicode'

setup(name=nam,
      version=pype.VERSION_,
      windows=[{"script": "pype.py",
                "icon_resources": [(1, os.path.join("icons", "pype.ico"))]}],
      data_files=[('', glob.glob('*.txt')+\
                   ['stc-styles.rc.cfg', 'pype.pyw', 'nosocket']),
                   ('icons', glob.glob(os.path.join('icons', '*.*')),
                  )],
      options = {"py2exe": {"packages": ["encodings"]}}
)
