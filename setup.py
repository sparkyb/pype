# setup.py
# to make a binary for windows from source...
# 1. download and install the py2exe utility from:
#      http://starship.python.net/crew/theller/py2exe/
# 2. run the following command:
#      python setup.py py2exe -w -f
from distutils.core import setup
import py2exe

setup(name="PyPE-win32",
      scripts=["pype.py"],
      data_files=[('', ('stc-styles.rc.cfg', 'readme.txt', 'gpl.txt', 'changelog.txt'))],
)
