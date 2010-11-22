
import wx

creation_date = 'Mon Aug 21 21:49:03 2006'
name = 'Run Current File'
hotkeydisplay = ""
hotkeyaccept = "Ctrl+Shift+F6"

def macro(self, data=None):
    if not self.dirname:
        print "can't start unnamed file"
        return
    
    if not data:
        extn = self.filename.split('.')[-1]
        fn = self.filename
        if ' ' in fn:
            fn = '"%s"'%fn
        dir = self.dirname
        if extn in ('py', 'pyw'):
            #if we don't embed it via os.system(), wx applications fail to
            #display the GUIs
            cmd = '''python -c "import os;os.system('python -u %s')"'''%(fn.replace('"', '\\"'))
        ## elif extn in ('tex',):
            ## cmd = 'pdflatex %s'%fn
        else:
            print "don't know how to run file type %r"%extn
            return
        data = (dir, cmd)
        
    #find or start a command output shell
    ts = type(self)
    for i,j in enumerate(self.notebook):
        if not isinstance(j, ts) and j.filter == 0 and not j.restartable and j.restart:
            break
    else:
        #otherwise create one
        self.root.newTab('', ' ', 0, 3)
        wx.CallAfter(macro, self, data)
        return
    
    j._Restart(data)
    wx.CallAfter(self.notebook.SetSelection, i)
