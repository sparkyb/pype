
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


#system imports
import os

#site-packages imports
import wx

#local imports
import filehistory

#Why should I use an object when a closure works just as well?
#God this is such a hack, but it makes me smile.
def WorkspaceMenu(parentmenu, parentwindow, workspaces, workspace_order):
    
    def OnCloseAll(event):
        self = parentwindow
        sel = self.control.GetSelection()
        cnt = self.control.GetPageCount()
        try:
            for i in xrange(cnt):
                win = self.control.GetPage(i).GetWindow1()
                
                #Yeah, I know that using a function that is placed in the
                #module's namespace AFTER import is bad form, but I do it
                #anyways.
                if isdirty(win):
                    self.control.SetSelection(i)
                    self.sharedsave(win)
        except cancelled:
            event.Skip()
            return
        self.starting = 1
        for i in xrange(cnt-1, -1, -1):
            self.OnClose(None, i, self.control.GetPage(i).GetWindow1())
        self.starting = 0
    
    def OnSave(event):
        #check for dirty and unnamed files...
        self = parentwindow
        sel = self.control.GetSelection()
        cnt = self.control.GetPageCount()
        d = 0
        l = []
        for i in xrange(cnt):
            win = self.control.GetPage(i).GetWindow1()
            data = os.path.join(win.dirname, win.filename).encode('ascii')
            d += win.dirty and data == ' '
            if data != ' ':
                l.append(data)
        
        if d:
            self.dialog("Cannot save workspace with\nmodified untitled documents.", "Workspace Save Aborted!")
            return
        
        #get the name of the workspace
        while 1:
        
            dlg = wx.TextEntryDialog(parentwindow, "What would you like this workspace to be called?", "Workspace name", pos=(0,0))
            if openmenu.last:
                dlg.SetValue(openmenu.last)
            rslt = dlg.ShowModal()
            workspacename = dlg.GetValue()
            dlg.Destroy()
            if rslt != wx.ID_OK:
                self.SetStatusText("Workspace save cancelled")
                return
            
            wn = workspacename.strip()
            
            #check for usable name
            if not wn:
                self.SetStatusText("Workspace save cancelled")
                return
            
            #check for unused name
            if wn.lower() in [i.lower() for i in workspace_order]:
                if self.dialog("Are you sure you want to replace\nthe pre-existing workspace:\n%s"%wn.lower(), "Duplicate Workspace", wx.YES_NO) != wx.ID_YES:
                    continue
            
            break
        
        #remove potential duplicates
        workspace_order[:] = [i for i in workspace_order if i.lower() != wn.lower() or openmenu.ItemRemove(i) or deletemenu.ItemRemove(i)]
        x = dict(workspaces)
        workspaces.clear()
        for i in workspace_order:
            workspaces[i] = x[i]
        
        #handle workspace ordering
        workspace_order.insert(0, wn)
        workspaces[wn] = l
        openmenu.ItemAdd(wn)
        deletemenu.ItemAdd(wn)
    
    def OnOpen(label):
        ## print "opening workspace"
        
        #handle ordering of workspaces
        if label in workspace_order:
            workspace_order.remove(label)
        
        workspace_order.insert(0, label)
        
        #fetch the workspace
        ws = workspaces.get(label, [])
        
        #open all documents in the workspace
        parentwindow.OnDrop(ws)
    
    def OnDelete(label):
        ## print "deleting workspace..."
        #delete the workspace and fix workspace order
        
        if label in workspace_order:
            workspace_order.remove(label)
        workspaces.pop(label, None)
    
    #code that actually modifies the menu
    if 1:
        closeall = wx.NewId()
        parentmenu.Append(closeall, "Close All Documents",
                        "Closes all open documents, asking to save changes on modified files")
        wx.EVT_MENU(parentwindow, closeall, OnCloseAll)
        parentmenu.AppendSeparator()
        nwksid = wx.NewId()
        parentmenu.Append(nwksid, "Save Workspace",
                        "Saves the current workspace, aborts if modified and unnamed files are open")
        wx.EVT_MENU(parentwindow, nwksid, OnSave)
        
        openmenu = filehistory.FileHistory(parentwindow, callback=[OnOpen], seq=workspace_order)
        deletemenu = filehistory.FileHistory(parentwindow, remove=1,
                                callback=[openmenu.ItemRemove, OnDelete],
                                seq=workspace_order,
                                delmsg=("Are you sure you want to delete the workspace:\n%s",
                                        "Delete Workspace?"))
        openmenu.callback.append(deletemenu.ItemAdd)
        parentmenu.AppendMenu(wx.NewId(), "Open Workspace", openmenu)
        parentmenu.AppendMenu(wx.NewId(), "Delete Workspace", deletemenu)
        parentmenu.AppendSeparator()

