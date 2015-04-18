
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import re
import wx
import wx.stc

import scheduler

class OnCloseBar: #embedded callback to destroy the findbar on removal
    def __init__(self, control):
        self.c = control
    def __call__(self, *args):
        self.c.savePreferences()
        self.c.parent.Unsplit()
        self.c.Destroy()
        del self.c

word = dict.fromkeys(map(ord, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))
non_word = dict.fromkeys([chr(i) for i in xrange(256) if i not in word])

MEM_LEAK_TEST = 0
OCOUNTLIMIT = COUNTLIMIT = 20

class ReplaceBar(wx.Panel):
    def __init__(self, parent, root):
        #init the object
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.parent = parent
        self.root = root
        
        #state variables
        self._lastcall = self.OnFindN
        self.incr = 1
        self.loop = 0
        self.shiftdown = 0
        self.buttons = []
        self.replacing = 0
        self.wholeword = 0
        
        self.replace_t = Timer(self._replace_again1, None)
        self._replace_args = None
        
        self.replace_t2 = Timer(self._re_replace_again1, None)
        self._re_replace_args = None
        
        prefs = self.readPreferences()
        self.setup()
        
    def setup(self):
        """
        Layout the panel controls.
        """
        
        prefs = self.preferences
        
        self.sizer = wx.GridBagSizer(5, 5)
        
        #textbox
        if self.root.getglobal('no_findbar_history'):
            self.box1 = box1 = wx.TextCtrl(self, -1, size=(125, -1), style=wx.TE_PROCESS_ENTER)
            if prefs['find']:
                box1.SetValue(prefs['find'][0])
        else:
            self.box1 = box1 = wx.ComboBox(self, -1, choices=prefs['find'], size=(125, -1), style=wx.TE_PROCESS_ENTER)
            if prefs['find']:
                box1.SetStringSelection(prefs['find'][0])
            box1.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        #box1.SetInsertionPoint(0)
        box1.Bind(wx.EVT_TEXT, self.OnChar)
        box1.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        box1.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        box1.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        box1.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.box1 = box1
        self.sizer.Add(box1, (0,0), flag=wx.EXPAND|wx.RIGHT, border=5)
        
        #find next and previous buttons
        self.addbutton(self.sizer, self, "Find Next", self.OnFindN, (0,1))
        self.addbutton(self.sizer, self, "Find Previous", self.OnFindP, (0,2))
        
        #match case toggle, along with re-calling the last find operation when
        #it is switched
        if DOUBLE_ROW_ONE:
            ss = wx.BoxSizer(wx.VERTICAL)
        if USE_BOX_SIZERS and not DOUBLE_ROW_ONE:
            ss = wx.BoxSizer(wx.HORIZONTAL)
        
        self.case = wx.CheckBox(self, -1, "Match Case")
        if USE_MINI_CHECKBOXES:
            self.case.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        if USE_BOX_SIZERS or DOUBLE_ROW_ONE:
            ss.Add(self.case, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        else:
            self.sizer.Add(self.case, (0,3), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        self.case.SetValue(prefs['case'])
        self.wrap = wx.CheckBox(self, -1, "Wrap Search")
        if USE_MINI_CHECKBOXES:
            self.wrap.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        self.wrap.SetValue(prefs['wrap'])
        if USE_BOX_SIZERS or DOUBLE_ROW_ONE:
            ss.Add(self.wrap, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        else:
            self.sizer.Add(self.wrap, (0,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        self.regex = wx.CheckBox(self, -1, "Regular Expression")
        if USE_MINI_CHECKBOXES:
            self.regex.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        if USE_BOX_SIZERS or DOUBLE_ROW_ONE:
            ss.Add(self.regex, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        else:
            self.sizer.Add(self.regex, (0,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
        self.regex.SetValue(prefs['regex'])
        
        if DOUBLE_ROW_ONE:
            if not USE_BOX_SIZERS:
                self.sizer.Add(ss, (0,3), flag=wx.EXPAND|wx.RIGHT, border=5)
            else:
                ss2 = wx.BoxSizer(wx.HORIZONTAL)
                ss2.Add(ss, 0, wx.EXPAND|wx.RIGHT, border=5)
                ss = ss2
        
        #close button
        self.close = OnCloseBar(self)
        if USE_BOX_SIZERS:
            ss.Add(wx.StaticText(self), 1, wx.EXPAND)
            self.closebutton = self.addbutton(ss, self, "Close", self.close, 0)
            self.sizer.Add(ss, (0,3), flag=wx.EXPAND)
        else:
            self.closebutton = self.addbutton(self.sizer, self, "Close", self.close, (0,6-bool(DOUBLE_ROW_ONE)))
        
        if isinstance(self, FindBar):
            ## self.box1.MoveAfterInTabOrder(self.closebutton)
            return self.finish_setup()
        
        if self.root.getglobal('no_findbar_history'):
            self.box2 = box2 = wx.TextCtrl(self, -1, size=(125, -1))
            if prefs['replace']:
                box2.SetValue(prefs['replace'][0])
        else:
            self.box2 = box2 = wx.ComboBox(self, -1, choices=prefs['replace'], size=(125, -1))
            if prefs['replace']:
                box2.SetStringSelection(prefs['replace'][0])
        box2.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.sizer.Add(box2, (1,0), flag=wx.EXPAND|wx.RIGHT, border=5)
        
        self.addbutton(self.sizer, self, "Replace", self.OnReplace, (1,1))
        self.addbutton(self.sizer, self, "Replace All", self.OnReplaceAll, (1,2))
        
        ss = wx.BoxSizer(wx.HORIZONTAL)
        if USE_BOX_SIZERS:
            self.addbutton(ss, self, "Replace in Selection", self.OnReplaceSel, 0)
        else:
            self.addbutton(self.sizer, self, "Replace in Selection", self.OnReplaceSel, (1,3))
        self.smartcase = wx.CheckBox(self, -1, "Smart Case")
        if USE_MINI_CHECKBOXES:
            self.smartcase.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        self.smartcase.SetValue(prefs['smartcase'])
        if USE_BOX_SIZERS:
            ss.Add(self.smartcase, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)
            self.sizer.Add(ss, (1,3), flag=wx.EXPAND)
        else:
            self.sizer.Add(self.smartcase, (1,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
        
        ## self.box1.MoveAfterInTabOrder(self.smartcase)
        self.finish_setup()

    def finish_setup(self):
        self.sizer.AddGrowableCol(0)
        
        self.sizer.Fit(self)
        self.SetSizer(self.sizer)

    def addbutton(self, sizer, control, alt, fcn, pos):
        t2 = wx.Button(control, -1, alt, style=wx.NO_BORDER)
        wx.EVT_BUTTON(control, t2.GetId(), fcn)
        flags = wx.RIGHT
        if type(pos) is tuple:
            #first row buttons are longer than second row buttons
            if pos[0] == 0:
                flags |= wx.ALIGN_CENTER_VERTICAL
            else:
                flags |= wx.EXPAND
        border = 5
        if alt == 'Close':
            #move the close button to the right
            flags |= wx.ALIGN_RIGHT
            #remove the right border on the close button
            flags ^= wx.RIGHT
        sizer.Add(t2, pos, flag=flags, border=5)
        if type(pos) is tuple and pos[1] == 1:
            self.buttons.append(t2)
        return t2

    def status(self, text):
        self.root.SetStatusText(text, log=0)

    def lastcall(self, evt):
        self._lastcall(evt)

    def OnChar(self, evt):
        #handle updating the background color
        if self.box1.GetBackgroundColour() != wx.WHITE:
            self.box1.SetBackgroundColour(wx.WHITE)
            self.status('')
            self.Refresh()
        
        if not isinstance(self, FindBar):
            return

        #search in whatever direction we were before
        if self._lastcall == self.OnFindN and not self.regex.GetValue():
            self._lastcall(evt, 1)

    def OnNotFound(self):
        self.box1.SetBackgroundColour(wx.RED)
        self.status("Search string was not found.")
        self.Refresh()

    def getFinds(self, evt, which=0):
        findTxt = self.box1
        if which:
            findTxt = self.box2
        findTxt = findTxt.GetValue()
        matchcase = self.case.GetValue() and wx.FR_MATCHCASE
        if not findTxt:
            if not which:
                if evt:
                    evt.Skip()
                raise cancelled
            return "", None, None, None
        
        #python strings in find automatically handled
        findTxt = self.root.getglobal('str_unrepr')(findTxt)
       
        #nothing to find!
        if not findTxt:
            if not which:
                if evt:
                    evt.Skip()
                raise cancelled
            return "", None, None, None
        
        regex = self.regex.GetValue()
        if (regex and not which):
            try:
                findTxt = re.compile(findTxt, not matchcase and re.I or 0)
            except:
                regex = 0
        
        win = self.parent.GetWindow1()
        return findTxt, matchcase, regex, win

    def sel(self, posns, posne, msg, win):
        if self.box1.GetBackgroundColour() != wx.WHITE:
            self.box1.SetBackgroundColour(wx.WHITE)
            self.status('')
            self.Refresh()
        self.status(msg)
        line = win.LineFromPosition(posns)
        win.GotoLine(line)
        posns, posne = self.getRange(win, posns, posne-posns)
        win.SetSelection(posns, posne)
        win.EnsureVisible(line)
        win.EnsureCaretVisible()
    
    def getRange(self, win, start, chars, dire=1):
        end = start
        if dire==1:
            fcn = win.PositionAfter
        else:
            fcn = win.PositionBefore
        for i in xrange(chars):
            z = fcn(end)
            y = win.GetCharAt(end)
            x = abs(z-end)==2 and (((dire==1) and (y == 13)) or ((dire==0) and (y == 10)))
            ## print y, z-end
            end = z - x
        return start, end
    
    def isWholeWord(self, start, chars, win):
        #we may need to use this for unicode whole word checks
        start, end = self.getRange(win, start, chars)
        if start != 0:
            if win.GetCharAt(win.PositionBefore(start)) not in non_word:
                return 0
        
        if end != win.GetTextLength():
            if win.GetCharAt(win.PositionAfter(end)) not in non_word:
                return 0
        
        return 1

    def OnFindN(self, evt, incr=0):
        self._lastcall = self.OnFindN
        self.incr = incr
        findTxt, matchcase, regex, win = self.getFinds(evt)
        flags = wx.FR_DOWN|matchcase
        if self.wholeword:
            flags |= wx.stc.STC_FIND_WHOLEWORD
        
        #handle finding next item, handling wrap-arounds as necessary
        gs = win.GetSelection()
        gs = min(gs), max(gs)
        st = gs[1-incr]
        if (regex):
            match = findTxt.search(win.GetTextUTF8(), st, win.GetTextLength())
            if (match):
                self.sel(match.start(), match.end(), '', win)
                self.loop = 0
                return
        else:
            posn = win.FindText(st, win.GetTextLength(), findTxt, flags)
            if posn != -1:
                self.sel(posn, posn+len(findTxt), '', win)
                self.loop = 0
                return
        
        self.loop = 1

        if self.wrap.GetValue() and st != 0:
            if (regex):
                match = findTxt.search(win.GetText())
                if (match):
                    self.sel(match.start(), match.end(), "Reached end of document, continued from start.", win)
                    self.loop = 0
                    return
            else:
                posn = win.FindText(0, win.GetTextLength(), findTxt, flags)
                if posn != -1:
                    self.sel(posn, posn+len(findTxt), "Reached end of document, continued from start.", win)
                    return
            
        self.OnNotFound()
    
    def OnFindP(self, evt, incr=0):
        self._lastcall = self.OnFindP
        self.incr = 0
        findTxt, matchcase, regex, win = self.getFinds(evt)
        
        if (regex):
            self.status("Can't search backwards with a regular expression.")
            return
        
        flags = matchcase
        if self.wholeword:
            flags |= wx.stc.STC_FIND_WHOLEWORD
        
        
        #handle finding previous item, handling wrap-arounds as necessary
        st = min(self.getRange(win, min(win.GetSelection()), len(findTxt), 0))
        #print win.GetSelection(), st, 
        posn = win.FindText(st, 0, findTxt, flags)
        if posn != -1:
            self.sel(posn, posn+len(findTxt), '', win)
            self.loop = 0
            return
        
        if self.wrap.GetValue() and st != win.GetTextLength():
            posn = win.FindText(win.GetTextLength(), 0, findTxt, flags)
        self.loop = 1
        
        if posn != -1:
            self.sel(posn, posn+len(findTxt), "Reached start of document, continued from end.", win)
            return
        
        self.OnNotFound()
    
    def OnKeyDown(self, evt):
        if self.FindFocus() == self.box1:
            self.wholeword = 0
        kc = evt.GetKeyCode()
        if kc == wx.WXK_ESCAPE:
            p = self.parent.GetWindow1()
            self.close()
            p.SetFocus()
            return
        elif kc == wx.WXK_SHIFT and self.FindFocus() == self.box1:
            self.shiftdown = 1
        ## elif kc == wx.WXK_TAB:
            ## foc = self.FindFocus()
            ## if foc == self.box1:
                ## return self.buttons[0].SetFocus()
            ## elif len(self.buttons) == 2 and foc == self.box2:
                ## return self.buttons[1].SetFocus()
        if evt:
            evt.Skip()
    
    def OnKeyUp(self, evt):
        if evt.GetKeyCode() == wx.WXK_SHIFT:
            self.shiftdown = 0
        if evt:
            evt.Skip()
    
    def OnEnter(self, evt):
        if self.shiftdown:
            return self.OnFindP(evt)
        return self.OnFindN(evt)
    
    def OnKillFocus(self, evt):
        self.shiftdown = 0
        if evt:
            evt.Skip()
    
    def OnSetFocus(self, evt):
        self.box1.SetMark(0, self.box1.GetLastPosition())
        if evt:
            evt.Skip()

    def OnReplace(self, evt):
        findTxt, matchcase, regex, win = self.getFinds(evt)
        regex = self.regex.GetValue()
        sel = win.GetSelection()
        if sel[0] == sel[1]:
            self.OnFindN(evt)
            return (-1, -1), 0
        else:
            a = win.GetTextRange(sel[0], sel[1])
            if (regex):
                match = findTxt.search(win.GetText(),sel[0],sel[1])
                if (not match or match.start()!=sel[0] or match.end()!=sel[1]):
                    self.OnFindN(evt)
                    return (-1, -1), 0
            else:
                if (matchcase and a != findTxt) or \
                   (not matchcase and a.lower() != findTxt.lower()):
                    self.OnFindN(evt)
                    return (-1, -1), 0
            
        
        replaceTxt = self.getFinds(None, 1)[0]
        if (regex):
            replaceTxt = findTxt.sub(replaceTxt,a)
        findTxt = a
        
        if self.smartcase.GetValue():
            if findTxt.upper() == findTxt:
                ## print "all upper", findTxt
                replaceTxt = replaceTxt.upper()
            elif findTxt.lower() == findTxt:
                ## print "all lower", findTxt
                replaceTxt = replaceTxt.lower()
            elif len(findTxt) == len(replaceTxt):
                ## print "smartcasing", findTxt
                r = []
                for i,j in zip(findTxt, replaceTxt):
                    if i.isupper():
                        r.append(j.upper())
                    elif i.islower():
                        r.append(j.lower())
                    else:
                        r.append(j)
                replaceTxt = ''.join(r)
            elif findTxt and replaceTxt and findTxt[:1].upper() == findTxt[:1]:
                ## print "first upper", findTxt
                replaceTxt = replaceTxt[:1].upper() + replaceTxt[1:]
            elif findTxt and replaceTxt and findTxt[:1].lower() == findTxt[:1]:
                ## print "first lower", findTxt
                replaceTxt = replaceTxt[:1].lower() + replaceTxt[1:]
        
        sel = win.GetSelection()
        if win.CanEdit():
            win.ReplaceSelection(replaceTxt)
            #fix for unicode...
            win.SetSelection(min(sel), min(sel)+len(replaceTxt))
            self.OnFindN(evt)
            
            return sel, len(findTxt)-len(replaceTxt)
        else:
            return (max(sel), max(sel)), 0
    
    def _replaceAll(self, evt, ris):
        win = self.parent.GetWindow1()
        ostart, oend = win.GetSelection()
        
        #ris = self.replinsel.GetValue()
        win.BeginUndoAction()
        try:
            if ris:
                win.SetSelection(ostart, ostart)
            else:
                win.SetSelection(0, 0)
            
            self.loop = 0
            failed = 0
            while not self.loop and failed < 2:
                #check for range...
                sel = win.GetSelection()
                if ris and (sel[0] < ostart or sel[1] > oend):
                    break
                #find/replace next item
                (lsel, rsel), delta = self.OnReplace(evt)
                ## print (lsel, rsel), delta, repr(win.GetTextRange(lsel, rsel)), self.loop
                #if nothing found, continue
                if lsel == -1:
                    continue
                #if change was entirely in the old selection...
                elif ostart <= lsel and rsel <= oend:
                    oend -= delta
                #original selection is encompassed by the replacement.
                elif lsel <= ostart and rsel >= oend:
                    ostart = oend = lsel
                #replaced portion is to the left of the original selection
                elif rsel < ostart:
                    ostart -= delta
                    oend -= delta
                try:
                    wx.Yield()
                except:
                    pass
            ## print self.loop, failed
            
            self.sel(ostart, oend, '', win)
            win.SetFocus()
        finally:
            win.EndUndoAction()
    
    def replaceAll(self, evt, ris):
        win = self.parent.GetWindow1()
        ostart, oend = win.GetSelection()
        
        #ris = self.replinsel.GetValue()
        if not MEM_LEAK_TEST: win.BeginUndoAction()
        if ris:
            win.SetSelection(ostart, ostart)
        else:
            win.SetSelection(0, 0)
        self.OnFindN(None, ris)
        
        self.replacing = 1
        wx.CallAfter(self.ReentrantReplace, (ostart, oend, ris, win))

    def ReentrantReplace(self, state):
        global COUNTLIMIT
        COUNTLIMIT = min(1000, int(COUNTLIMIT*1.5))
        ostart, oend, ris, win = state
        
        if not win:
            return
        
        try:
            self.loop
        except:
            return
        
        cont = 1
        count = 0
        while not self.loop:
            sel = win.GetSelection()
            if ris and (sel[0] < ostart or sel[1] > oend):
                cont = 0
                break
            #find/replace next item
            (lsel, rsel), delta = self.OnReplace(None)
            ## print (lsel, rsel), delta, repr(win.GetTextRange(lsel, rsel)), self.loop
            #if nothing found, continue
            if lsel == -1:
                continue
            #if change was entirely in the old selection...
            elif ostart <= lsel and rsel <= oend:
                oend -= delta
            #original selection is encompassed by the replacement.
            elif lsel <= ostart and rsel >= oend:
                ostart = oend = lsel
            #replaced portion is to the left of the original selection
            elif rsel < ostart:
                ostart -= delta
                oend -= delta
            count += 1
            if count >= COUNTLIMIT and not self.loop:
                break
        else:
            cont = 0
        
        if MEM_LEAK_TEST:
            win.EmptyUndoBuffer()
        
        if cont:
            if MEM_LEAK_TEST:
                scheduler.FutureCall(1, self.ReentrantReplace, (ostart, oend, ris, win))
            elif 1:
                wx.CallAfter(self.ReentrantReplace, (ostart, oend, ris, win))
            else:
                self._replace_again2((ostart, oend, ris, win))
        else:
            self.replacing = 0
            self.sel(ostart, oend, '', win)
            if self.root.control.GetPageCount() and \
               self.root.control.GetCurrentPage() == self.parent:
                win.SetFocus()
            if not MEM_LEAK_TEST:
                win.EndUndoAction()
    
    def _replace_again1(self, evt):
        self._replace_args, args = None, self._replace_args
        self.ReentrantReplace(args)
    
    def _replace_again2(self, args):
        self._replace_args = args
        self.replace_t.Start(1, wx.TIMER_ONE_SHOT)
    
    def OnReplaceAll(self, evt):
        global COUNTLIMIT
        if self.replacing:
            return
        COUNTLIMIT = OCOUNTLIMIT
        self.replaceAll(evt, 0)
    
    def OnReplaceSel(self, evt):
        if self.replacing:
            return
        self.replaceAll(evt, 1)
    
    def _simple_re_all(self, expression, template, flags=0):
        win = self.parent.GetWindow1()
        text = wx.stc.StyledTextCtrl.GetText(win)
        c = re.compile(expression, flags)
        win.SetText(c.sub(template, text))
    
    def _replace_re_all(self, expression, template, flags=0):
        win = self.parent.GetWindow1()
        text = wx.stc.StyledTextCtrl.GetText(win)
        c = re.compile(expression, flags)
        
        #need to implement the equivalent of...
        ## win.SetText(c.sub(template, text))
        
        lastpw = 0
        lastp = 0
        c = re.compile(expression, flags)
        try:
            _1, win.recording = win.recording, 0
            win.BeginUndoAction()
            try:
                for match in c.finditer(text):
                    start, end = match.span()
                    plain = match.group()
                    plainn = match.expand(template)
                    
                    plainl = len(plain.encode('utf-8'))
                    lastpw += len(text[lastp:start].encode('utf-8'))
                    
                    assert win.GetTextRange(lastpw, lastpw+plainl) == plain
                    
                    win.SetSelection(lastpw, lastpw+plainl)
                    win.ReplaceSelection(plainn)
                    plainnl = len(plainn.encode('utf-8'))
                    
                    assert win.GetTextRange(lastpw, lastpw+plainnl) == plainn
                    
                    lastpw += plainnl
                    lastp = end
            finally:
                win.EndUndoAction()
                win.recording = _1
        except:
            _1, win.recording = win.recording, 0
            win.Undo()
            win.recording = _1
            raise
    
    def _re_replace_again1(self, evt):
        self._re_replace_args, args = None, self._re_replace_args
        wx.CallAfter(self.ReentrantRegularExpressionReplace, (args,))
    
    def _re_replace_again2(self, args):
        self._re_replace_args = args
        self.replace_t2.Start(1, wx.TIMER_ONE_SHOT)
    
    def REreplaceAll(self, expression, template, flags=0):
        win = self.parent.GetWindow1()
        lastpw = 0
        c = re.compile(expression, flags)
        _1, win.recording = win.recording, 0

        wx.CallAfter(self.ReentrantRegularExpressionReplace, (lastpw, c, template, _1, win))
    
    def ReentrantRegularExpressionReplace(self, state):
        global COUNTLIMIT
        COUNTLIMIT = min(1000, int(COUNTLIMIT*1.5))
        lastpw, c, template, _1, win = state
        
        lastp = 0
        cont = 1
        
        text = win.GetTextRange(lastpw, win.GetTextLength())
        for i, match in enumerate(c.finditer(text)):
            start, end = match.span()
            plain = match.group()
            plainn = match.expand(template)
            
            plainl = len(plain.encode('utf-8'))
            lastpw += len(text[lastp:start].encode('utf-8'))
            
            assert win.GetTextRange(lastpw, lastpw+plainl) == plain
            
            win.SetSelection(lastpw, lastpw+plainl)
            win.ReplaceSelection(plainn)
            plainnl = len(plainn.encode('utf-8'))
            
            assert win.GetTextRange(lastpw, lastpw+plainnl) == plainn
            
            lastpw += plainnl
            lastp = end
            if i == COUNTLIMIT-1:
                break
        else:
            cont = 0
        
        if MEM_LEAK_TEST:
            win.EmptyUndoBuffer()
        
        if cont:
            if MEM_LEAK_TEST:
                wx.FutureCall(1, self.ReentrantRegularExpressionReplace, (lastpw, c, template, _1, win))
            elif 1:
                wx.CallAfter(self.ReentrantRegularExpressionReplace, (lastpw, c, template, _1, win))
            else:
                self._re_replace_again2((lastpw, c, template, _1, win))
        else:
            if not MEM_LEAK_TEST:
                win.EndUndoAction()
                win.recording = _1
                
    #----------------------------------

    def readPreferences(self):
        try:
            prefs = self.parent.GetWindow1().findbarprefs
        except:
            prefs = self.parent.GetWindow1().findbarprefs = {}
        # Set the defaults individually so that adding options works
        # as expected.
        prefs.setdefault('prefs_version', 1)
        prefs.setdefault('find', [])
        prefs.setdefault('replace', [])
        prefs.setdefault('case', 0)
        prefs.setdefault('wrap', 1)
        prefs.setdefault('smartcase', 0)
        prefs.setdefault('regex', 0)
        #prefs.setdefault('multiline', 0)
        #prefs.setdefault('whole_word', 0)
        #prefs.setdefault('quoted', 0)
        #prefs.setdefault('commented', 0)

        self.preferences = prefs
        return prefs

    def savePreferences(self):
        def getlist(c):
            if not isinstance(c, wx.ComboBox):
                return [c.GetValue()]
            if self.root.getglobal('no_findbar_history'):
                return [c.GetValue()]
            cc = c.GetCount()
            e = [c.GetString(i) for i in xrange(cc)]
            e = [i for i in e if i]
            a = c.GetValue()
            if a:
                if a in e:
                    e.remove(a)
                e = [a] + e
            e = e[:10]
            ## if len(e) > cc:
                ## c.Append(e[-1])
            ## for i in xrange(len(e)):
                ## c.SetString(i, e[i])
            ## c.SetSelection(0)
            return e

        prefs = {
            'prefs_version': 1,
            'find': getlist(self.box1),
            'case': self.case.IsChecked(),
            'wrap': self.wrap.IsChecked(),
            #'regex': self.re.IsChecked(),
            #'multiline': self.multiline.IsChecked(),
            #'whole_word': self.ww.IsChecked(),
            #'quoted': self.quoted.IsChecked(),
            #'commented': self.commented.IsChecked(),
            }
        #if I am a replace bar, save the smartcase replacement option.
        if not isinstance(self, FindBar):
            prefs['replace'] = getlist(self.box2)
            prefs['smartcase'] = self.smartcase.IsChecked()
        
        self.parent.GetWindow1().findbarprefs.update(prefs)

#-----------------------------------------------------------------------------

class FindBar(ReplaceBar):
    """
    Embedded find in the current document
    """

USE_MINI_CHECKBOXES = 0
DOUBLE_ROW_ONE = 0
USE_BOX_SIZERS = 1

if __name__ == "__main__":
    ## Test Code to mess with layout
    # some dummy classes for prefs, etc.
    class Window1:
        findbarprefs = {}

    class root:
        def getglobal(self, key):
            return {}

    class TestFrame(wx.Frame):
        def __init__(self, *args, **kwargs):
            wx.Frame.__init__(self, *args, **kwargs)
            
            sizer = wx.BoxSizer(wx.VERTICAL)
            fb = FindBar(self, root())
            rb = ReplaceBar(self, root())
            
            sizer.Add(fb, 0, wx.EXPAND)
            sizer.Add((20,20))
            sizer.Add(rb, 0, wx.EXPAND)
            
            self.SetSizerAndFit(sizer)
            
        def GetWindow1(self):
            return Window1()

    app = wx.App(False)
           
    f = TestFrame(None)

    f.Show()
    wx.CallAfter(f.SendSizeEvent)
    app.MainLoop()
