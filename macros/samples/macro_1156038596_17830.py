
import wx
creation_date = 'Sat Aug 19 18:49:56 2006'
name = 'Run selected text in a Python Shell'
hotkeyaccept = 'Ctrl+Shift+F5'

def macro(self, data=''):
    self.lines.selectedlinesi = self.lines.selectedlinesi
    
    #get the lines if we don't already have some
    if not data:
        data = ''.join(self.lines.selectedlines)
        data = self._StripPrefix(data, 0, 1)
    if not data.strip():
        return
    #copy the text to the clipboard
    if not _pype.SetClipboardText(data):
        return
    
    #find some Python shell
    ts = type(self)
    for i,j in enumerate(self.notebook):
        if not isinstance(j, ts) and j.filter == 1:
            break
    else:
        #otherwise create one
        self.root.newTab('', ' ', 0, 1)
        wx.CallAfter(macro, self, data)
        return
    
    #select the shell, toss the current entry, and paste the text
    self.notebook.SetSelection(i)
    j.SetSelection(j.promptPosEnd, j.GetTextLength())
    j.ReplaceSelection('')
    j.Paste()
