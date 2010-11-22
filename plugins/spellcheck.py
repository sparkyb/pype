
import wx
import wx.stc
import wx.lib.scrolledpanel as scrolled
import os
import time
import traceback
import sys

try:
    UNICODE = sys.modules['__main__'].UNICODE
except:
    UNICODE = 0

class defdict(dict):
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return key

goodch = dict.fromkeys('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
transtable = ''.join([(' ', i.lower())[i in goodch] for i in [chr(j) for j in xrange(256)]])


non_word = defdict([(chr(i), ' ') for i in xrange(256) if chr(i) not in goodch])

fil = os.path.join(os.path.normpath(os.path.join(os.getcwd(),
                                                 os.path.split(__file__)[0])),
                   'dictionary.txt')

dictionary = {}
alphabet = 'abcdefghijklmnopqrstuvwxyz'

def _dri(word, alphabet):
    for i in xrange(len(word)):
        x = word[:i]
        y = word[i+1:]
        #will attempt to delete every individual character from the word
        yield x + y
        z = word[i:]
        for j in alphabet:
            #will attempt to replace every individual character from the word
            #with another character
            yield x + j + y
            #will attempt to insert a new character into every position in the
            #word except for the last
            yield x + j + z
        #will attempt to swap every internal pair of characters
        yield x + word[i+1:i+2] + word[i:i+1] + word[i+2:]
    for j in alphabet:
        #inserts a new character at the end of the word
        yield word + j


def suggest(word, dcts):
    _a = alphabet
    x = {}
    for i in _dri(word, _a):
        if i not in x:
            for j in dcts:
                if i in j:
                    x[i] = None
                    break
    x = x.keys()
    x.sort()
    return x

class SpellCheck(scrolled.ScrolledPanel):
    def __init__(self, parent, root):
        scrolled.ScrolledPanel.__init__(self, parent, -1)
        
        self.document = None
        self.root = root
        self.funcdefs = {}
        self.dcts = {}
        self.start = 0
        
        ws = wx.BoxSizer(wx.HORIZONTAL)
        
#-------------------------- Left button/pref column --------------------------
        
        s = wx.BoxSizer(wx.VERTICAL)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        
        go = wx.Button(self, -1, "Check!")
        bs = go.GetDefaultSize()[1]
        go.SetToolTipString("Check spelling in the current document")
        s2.Add(go, 0, wx.RIGHT, 4)
        self.Bind(wx.EVT_BUTTON, self.OnSpellCheck, go)

        checks = wx.Button(self, -1, "Check Sel")
        checks.SetToolTipString("Check spelling in the selection of the current document")
        s2.Add(checks, 0)
        self.Bind(wx.EVT_BUTTON, self.OnSpellCheckSel, checks)

        s.Add(s2, 0, wx.ALL, 2)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.ignore_funcdefs = wx.CheckBox(self, -1, "Ignore Defs")
        self.ignore_funcdefs.SetToolTipString("If checked, will ignore all function definitions")
        s2.Add(self.ignore_funcdefs, 0, wx.TOP|wx.BOTTOM, 6)
        
        clear = wx.Button(self, -1, "Clear")
        clear.SetToolTipString("Clear the results of the previous spell check")
        s2.Add(clear, 0, wx.LEFT, 4)
        self.Bind(wx.EVT_BUTTON, self.OnClear, clear)

        s.Add(s2, 0, wx.ALL|wx.EXPAND, 2)
        
        ## ws.Add(s, 0, wx.ALL|wx.EXPAND, 2)
        
#------------------------ Custom dictionaries column -------------------------

        s.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 4)

        ## s = wx.BoxSizer(wx.VERTICAL)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        
        s2.Add(wx.StaticText(self, -1, "Custom Dictionaries:"), 1, wx.RIGHT|wx.ALIGN_LEFT|wx.EXPAND, 4)
        
        s2.Add(wx.StaticText(self, -1, ""), 0, wx.EXPAND)
        
        addd = wx.Button(self, -1, "+", style=wx.BU_EXACTFIT)
        addd.SetToolTipString("Add a new custom dictionary")
        s2.Add(addd, 0, wx.RIGHT|wx.ALIGN_RIGHT, 4)
        self.Bind(wx.EVT_BUTTON, self.OnAddD, addd)
        
        deld = wx.Button(self, -1, "-", style=wx.BU_EXACTFIT)
        deld.SetToolTipString("Remove a custom dictionary")
        s2.Add(deld, 0, wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_BUTTON, self.OnDelD, deld)
        
        s.Add(s2, 0, wx.ALL, 2)
        
        s.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 2)
        
        _ = list(self.root.config['DICTIONARIES'])
        _.sort()
        self.dictionaries = wx.CheckListBox(self, -1, choices=_)
        s.Add(self.dictionaries, 1, wx.EXPAND)
        
        ws.Add(s, 0, wx.ALL|wx.EXPAND, 2)
        
#---------------------------- Misspellings column ----------------------------
        
        s = wx.BoxSizer(wx.VERTICAL)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add(wx.StaticText(self, -1, "Possible Misspellings:"), 1, wx.ALIGN_LEFT|wx.EXPAND, 4)
        
        cha = wx.Button(self, -1, "./ All", style=wx.BU_EXACTFIT)
        cha.SetToolTipString("Make sure all of the 'Possible Misspellings' are checked")
        s2.Add(cha, 0, wx.RIGHT, 4)
        self.Bind(wx.EVT_BUTTON, self.OnCheckAll, cha)
        
        add = wx.Button(self, -1, "+./", style=wx.BU_EXACTFIT)
        add.SetToolTipString("Add the checked words to a custom dictionary")
        s2.Add(add, 0)
        self.Bind(wx.EVT_BUTTON, self.OnAdd, add)

        ignore = wx.Button(self, -1, "- ./", style=wx.BU_EXACTFIT)
        ignore.SetToolTipString("Ignore the checked words while this document stays open")
        s2.Add(ignore, 0, wx.RIGHT, 4)
        self.Bind(wx.EVT_BUTTON, self.OnIgnore, ignore)
        
        s.Add(s2, 0, wx.ALL|wx.EXPAND, 2)
        s.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 2)
        
        self.badsp = wx.CheckListBox(self, -1, choices=[], style=wx.LB_SINGLE)
        s.Add(self.badsp, 1, wx.EXPAND)
        self.badsp.Bind(wx.EVT_LISTBOX, self.OnClick)
        
        ws.Add(s, 1, wx.ALL|wx.EXPAND, 2)
        
#---------------------------- Corrections column -----------------------------
        
        s = wx.BoxSizer(wx.VERTICAL)
        
        s.Add(wx.StaticText(self, -1, "Possible Corrections:", size=(-1, bs)), 0, wx.ALL|wx.ALIGN_CENTER|wx.EXPAND, 2)
        
        s.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 2)
        
        self.replsp = FindPrefixListBox(self, -1, choices=[], style=wx.LB_SINGLE)
        s.Add(self.replsp, 1, wx.EXPAND)
        self.replsp.Bind(wx.EVT_LISTBOX, self.OnClickRepl)
        
        ws.Add(s, 1, wx.ALL|wx.EXPAND, 2)

        self.SetSizer(ws)
        self.SetAutoLayout(1)
        self.SetupScrolling()
    
        wx.CallAfter(self.load_d)
        
    def load_d(self):
        rp = self.root.getglobal('runpath')
        df = os.path.join(rp, 'dictionary.txt')
        while os.path.exists(df):
            try:
                dct = open(df, 'rb').read()
            except Exception, why:
                self.root.SetStatusText("Dictionary load failed! %s"%why)
                break
            
            if dct.startswith('\xef\xbb\xbf'):
                dct = dct[3:]
            
            try:
                dct = dct.decode('utf-8')
            except:
                self.root.SetStatusText("Dictionary load failed!")
                traceback.print_exc()
                break
            
            x = dict.fromkeys(map(str, dct.split()))
            _ = x.pop('', None)
            
            if not UNICODE:
                for i in x:
                    if type(i) is unicode:
                        self.root.SetStatusText("Dictionary load failed!")
                        self.root.SetStatusText("You must use a unicode-enabled PyPE/wxPython for the given dictionary")
                        break
            dictionary.update(x)
            break
                    
        af = os.path.join(rp, 'alphabet.txt')
        while os.path.exists(af):
            try:
                ab = open(af, 'rb').read()
            except Exception, why:
                self.root.SetStatusText("Alphabet load failed! %s"%why)
                break
            
            if ab.startswith('\xef\xbb\xbf'):
                ab = ab[3:]
            
            try:
                ab = ab.decode('utf-8')
            except:
                self.root.SetStatusText("Alphabet load failed!")
                traceback.print_exc()
                break
            
            x = ''.join(ab.split())
            x = dict.fromkeys([str(i).lower() for i in x.split(',') if i]).keys()
            if not UNICODE:
                for i in x:
                    if type(i) is unicode:
                        self.root.SetStatusText("Alphabet load failed!")
                        self.root.SetStatusText("You must use a unicode-enabled PyPE/wxPython for the given alphabet")
                        break
            
            global alphabet
            alphabet = tuple(x)
            break
    
    def OnCheckAll(self, evt):
        for i in xrange(self.badsp.GetCount()):
            self.badsp.Check(i)
    
    def OnSpellCheckSel(self, evt):
        self.OnSpellCheck(evt, 1)
    
    def OnSpellCheck(self, evt, sel=0):
        num, win = self.root.getNumWin(evt)
        t = time.time()
        
        if win != self.document:
            self.document = win
            self.funcdefs.clear()
        
        if self.ignore_funcdefs.GetValue():
            self.funcdefs = dict.fromkeys([i.lower() for i in win.tooltips])
        else:
            self.funcdefs.clear()
        
        fd = self.funcdefs
        _dict = dictionary
        self.dcts = dcts = {}
        d = self.root.config["DICTIONARIES"]
        for i in xrange(self.dictionaries.GetCount()):
            if self.dictionaries.IsChecked(i):
                dcts.update(d[self.dictionaries.GetString(i)])
        
        words = {}
        if not sel:
            doc = wx.stc.StyledTextCtrl.GetText(win)
            self.start = 0
        else:
            doc = wx.stc.StyledTextCtrl.GetSelectedText(win)
            self.start = min(win.GetSelection())
        tt = transtable
        try:
            doc = doc.encode('ascii')
        except:
            tt = non_word
        
        wrds = doc.translate(tt).split()
        wc = len(wrds)
        for i in wrds:
            if i not in _dict and i not in fd and i not in win.ignore and i not in dcts:
                words[i] = words.get(i, 0) + 1
        del wrds
        words = words.items()
        words.sort()
        
        self.OnClear(evt)
        
        cnt = 0
        for i,j in words:
            if j > 1:
                i = "%s    (%i times)"%(i,j)
            cnt += j
            _ = self.badsp.Append(i)
            ## self.badsp.Check(self.badsp.GetCount()-1)
        self.root.SetStatusText("Found %i misspellings of %i words in %i words in %.1f seconds"%(cnt, len(words), wc, time.time()-t))
    
    def verify_and_select(self):
        #select the document...
        try:
            self.document.ignore
            for i,j in enumerate(self.root.control):
                if j == self.document:
                    self.root.control.SetSelection(i)
                    break
        except Exception, why:
            print why
            self.badsp.Clear()
            self.replsp.Clear()
            self.document = None
            self.funcdefs.clear()
            return 0
        return 1
    
    def verify_findbox(self, evt):
        self.root.OnShowReplacebar(evt)
        fb = self.document.GetParent().GetWindow2()
        fb.case.SetValue(0)
        fb.wrap.SetValue(1)
        x = self.badsp.GetStringSelection().split()[0]
        if fb.box1.GetValue() != x:
            fb.box1.SetValue(x)
        fb.box2.SetValue('')
        fb.wholeword = 1
        return fb
    
    def OnClick(self, evt):
        if not self.verify_and_select():
            return
        
        self.replsp.Clear()
        x = evt.GetString().split()[0]
        lst = suggest(x, (dictionary, self.funcdefs, self.dcts))
        for i in lst:
            _ = self.replsp.Append(i)
        
        fb = self.verify_findbox(evt)
        self.document.SetSelection(self.start, self.start)
        fb.OnFindN(evt)
        wx.CallAfter(self.badsp.SetFocus)
    
    def OnIgnore(self, evt):
        for i in xrange(self.badsp.GetCount()-1, -1, -1):
            if self.badsp.IsChecked(i):
                self.document.ignore[self.badsp.GetString(i).split()[0]] = None
                self.badsp.Delete(i)
    
    def OnClickRepl(self, evt):
        if not self.verify_and_select():
            return
        
        fb = self.verify_findbox(evt)
        fb.smartcase.SetValue(1)
        fb.box2.SetValue(evt.GetString().split()[0])
    
    def OnClear(self, evt):
        self.badsp.Clear()
        self.replsp.Clear()

    def OnAdd(self, evt):
        dct = self.root.config['DICTIONARIES']
        k = list(dct)
        k.sort()
        
        dlg = wx.SingleChoiceDialog(self,
            'Which dictionary do you want to add words to?', 'Which Dictionary?',
            k, wx.CHOICEDLG_STYLE)
        
        add = None
        if dlg.ShowModal() == wx.ID_OK:
            add = dlg.GetStringSelection()

        dlg.Destroy()
        
        if not add:
            return
        
        add = dct[add]
        i = 0
        for i in xrange(self.badsp.GetCount()-1, -1, -1):
            if self.badsp.IsChecked(i):
                add[self.badsp.GetString(i).split()[0]] = None
                self.badsp.Delete(i)

    def OnAddD(self, evt):
        dlg = wx.TextEntryDialog(self, "Dictionary Name?", "What would you like your new dictionary to be named?", "")
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp != wx.ID_OK:
            raise cancelled
        
        dct = self.root.config['DICTIONARIES']
        
        if valu in dct:
            self.root.SetStatusText('Dictionary adding failed, dictionary %s already exists'%valu)
            return
        elif not valu.strip():
            self.root.SetStatusText('Dictionary adding failed, cannot create unnamed dictionary')
            return
        
        dct[valu] = {}
        #refresh the dictionary list...
        
        insp = len([i for i in dct if i < valu])
        self.dictionaries.Insert(valu, insp)
        
        
    def OnDelD(self, evt):
        k = list(self.root.config['DICTIONARIES'])
        k.sort()
        
        dlg = wx.SingleChoiceDialog(self,
            'Which dictionary would\nyou like to delete?', 'Delete Dictionary?',
            k, wx.CHOICEDLG_STYLE)
        
        dele = None
        if dlg.ShowModal() == wx.ID_OK:
            dele = dlg.GetStringSelection()

        dlg.Destroy()
        if not dele:
            return
        
        dct = self.root.config['DICTIONARIES']
        
        if dct[dele]:
            #are you sure?
            dlg = wx.MessageDialog(self, '''\
                Are you sure you want to delete the custom dictionary: '%s'?
                It has %i words.'''.replace(16*' ', '')%(dele, len(dct[dele])),
                "Are you sure?", wx.OK|wx.CANCEL)
            retr = dlg.ShowModal()
            dlg.Destroy()
            if retr != wx.ID_OK:
                self.root.SetStatusText('Dictionary deletion cancelled')
                return
        
        del dct[dele]
        dsp = len([i for i in dct if i < dele])
        self.dictionaries.Delete(dsp)
        
#FindPrefixListBox derived from the wxPython demo
class FindPrefixListBox(wx.ListBox):
    def __init__(self, parent, id=-1, choices=[], style=wx.LB_SINGLE):
        wx.ListBox.__init__(self, parent, id, choices=choices, style=wx.LB_SINGLE)
        self.typedText = ''
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)

    def FindPrefix(self, prefix):
        self.log.WriteText('Looking for prefix: %s\n' % prefix)

        if prefix:
            prefix = prefix.lower()
            length = len(prefix)

            # Changed in 2.5 because ListBox.Number() is no longer supported.
            # ListBox.GetCount() is now the appropriate way to go.
            for x in xrange(self.GetCount()):
                text = self.GetString(x)
                text = text.lower()

                if text[:length] == prefix:
                    return x

        return -1

    def OnKey(self, evt):
        key = evt.GetKeyCode()

        if key >= 32 and key <= 127:
            self.typedText = self.typedText + chr(key)
            item = self.FindPrefix(self.typedText)

            if item != -1:
                self.SetSelection(item)

        elif key == wx.WXK_BACK:   # backspace removes one character and backs up
            self.typedText = self.typedText[:-1]

            if not self.typedText:
                self.SetSelection(0)
            else:
                item = self.FindPrefix(self.typedText)

                if item != -1:
                    self.SetSelection(item)
        else:
            self.typedText = ''
            evt.Skip()
