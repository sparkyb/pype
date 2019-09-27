
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


#system imports
import glob
import os
import pprint
import time

#site-packages imports
import wx

#local imports
import filehistory

workspacepath = os.path.join(_pype.homedir, 'workspaces')

#Why should I use an object when a closure works just as well?
#God this is such a hack, but it makes me smile.
def CreateWorkspaceMenus(parentmenu, parentwindow, workspaces, workspace_order):

    def SaveWorkspace(name, paths):
        path = os.path.join(workspacepath, name + '.txt')
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        f = open(path, "w")
        f.write(pprint.pformat(paths))
        f.close()

    def TouchWorkspace(name):
        try:
            os.utime(os.path.join(workspacepath, name + '.txt'), None)
        except:
            return

    def LoadWorkspaces():
        # load new format
        workspaces.clear()
        workspace_order[:] = []

        try:
            for dirpath, dirnames, filenames in os.walk(workspacepath):
                for path in glob.glob(os.path.join(dirpath, '*.txt')):
                    name = os.path.splitext(os.path.relpath(path, workspacepath))[0].replace('\\', '/')
                    f = open(path, 'r')
                    data = f.read()
                    f.close()
                    try:
                        workspaces[name] = _pype.unrepr(data)
                    except:
                        pass
                    else:
                        workspace_order.append(name)
        except:
            pass
        workspace_order.sort(key=lambda name: os.stat(os.path.join(workspacepath, name + '.txt')).st_mtime, reverse=True)

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
        SaveWorkspace(wn, l)
        openmenu.ItemAdd(wn)
        deletemenu.ItemAdd(wn)
    
    def OnOpen(label):
        ## print "opening workspace"
        
        #handle ordering of workspaces
        if label in workspace_order:
            workspace_order.remove(label)
        
        workspace_order.insert(0, label)

        TouchWorkspace(label)
        
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
        path = os.path.join(workspacepath, label + '.txt')
        try:
            os.remove(path)
        except:
            pass
        else:
            os.removedirs(os.path.dirname(path))

    # upgrade old format to new.
    for name in reversed(workspace_order):
        SaveWorkspace(name, workspaces[name])
        time.sleep(.5)

    LoadWorkspaces()

    #code that actually modifies the menu
    if 1:
        nwksid = wx.NewId()
        parentmenu.Append(nwksid, "Save Workspace",
                        "Saves the current workspace, aborts if modified and unnamed files are open")
        wx.EVT_MENU(parentwindow, nwksid, OnSave)
        
        openmenu = WorkspaceMenu(parentwindow, callback=[OnOpen], seq=workspace_order)
        deletemenu = WorkspaceMenu(parentwindow, remove=1,
                                callback=[openmenu.ItemRemove, OnDelete],
                                seq=workspace_order,
                                delmsg=("Are you sure you want to delete the workspace:\n%s",
                                        "Delete Workspace?"))
        openmenu.callback.append(deletemenu.ItemAdd)
        parentmenu.AppendMenu(wx.NewId(), "Open Workspace", openmenu)
        parentmenu.AppendMenu(wx.NewId(), "Delete Workspace", deletemenu)
        parentmenu.AppendSeparator()



class WorkspaceMenu(wx.Menu):
    def __init__(self, parent, name='', remove=0, callback=None, seq=[], delmsg=('', '')):
        self.delmsg = delmsg
        if name:
            wx.Menu.__init__(self, name)
        else:
            wx.Menu.__init__(self)
        
        self.remove = remove
        if not callback:
            self.callback = []
        else:
            self.callback = callback
        
        self.parent = parent

        self.submenus = {}
        self.items = {}
        self.names = {}

        for name in seq:
            parts = name.split('/')
            submenuname = ''
            submenu = self
            for part in parts[:-1]:
                submenuname += part
                if submenuname not in self.submenus:
                    self.submenus[submenuname] = submenu.AppendMenu(wx.NewId(), part, wx.Menu())
                submenu = self.submenus[submenuname].GetSubMenu()
                submenuname += '/'
            iid = wx.NewId()
            self.items[name] = submenu.Append(iid, parts[-1])
            self.names[iid] = name
            wx.EVT_MENU(self.parent, iid, self.OnClicked)
        
        self.last = None

    def ItemRemove(self, name):
        if name not in self.items:
            return
        if name == self.last:
            self.last = None
        item = self.items[name]
        del self.items[name]
        del self.names[item.GetId()]
        item.GetMenu().DeleteItem(item)
        name = os.path.dirname(name)
        while name:
            if self.submenus[name].GetSubMenu().GetMenuItemCount() == 0:
                self.submenus[name].GetMenu().DeleteItem(self.submenus[name])
                del self.submenus[name]
            else:
                break
            name = os.path.dirname(name)
    
    def ItemAdd(self, name):
        self.last = name
        
        parts = name.split('/')
        submenuname = ''
        submenu = self
        for part in parts[:-1]:
            submenuname += part
            if submenuname not in self.submenus:
                self.submenus[submenuname] = submenu.PrependMenu(wx.NewId(), part, wx.Menu())
            else:
                submenu.RemoveItem(self.submenus[submenuname])
                submenu.PrependItem(self.submenus[submenuname])
            submenu = self.submenus[submenuname].GetSubMenu()
            submenuname += '/'

        if name in self.items:
            item = self.items[name]
            submenu.RemoveItem(item)
            submenu.PrependItem(item)
        else:
            iid = wx.NewId()
            self.items[name] = submenu.Prepend(iid, parts[-1])
            self.names[iid] = name
            wx.EVT_MENU(self.parent, iid, self.OnClicked)
        
    def OnClicked(self, evt):
        eid = evt.GetId()
        if eid not in self.names:
            return
        name = self.names[eid]
        if self.remove:
            if filehistory.root.dialog(self.delmsg[0]%name, self.delmsg[1], wx.OK|wx.CANCEL)&1 != 0:
                return
            self.ItemRemove(name)
        else:
            self.ItemAdd(name)
        for i in self.callback:
            i(name)
