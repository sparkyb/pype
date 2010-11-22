Readme/Help for PyPE 1.0 (Python Programmer's Editor')
http://come.to/josiah

PyPE is copyright (c) 2003 Josiah Carlson.

This software is licensed under the GPL (GNU General Public License) as it
appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as gpl.txt.

The included STCStyleEditor.py, which is used to support styles, was released
under the wxWindows license and is copyright (c) 2001 - 2002 Riaan Booysen.
The copy included was also distributed with wxPython version 2.4.1.2 for
Python 2.2, and was not modified in any form.

The included stc-styles.rc.cfg was slightly modified from the original version
in order to no cause exceptions during style changes, and was also distributed
with wxPython version 2.4.1.2 for Python 2.2

If you do not also receive a copy of gpl.txt with your version of this
software, please inform the me of the violation at the web page at the top of
this document.

#------------------------------- Requirements --------------------------------
PyPE has only been tested on Python 2.2 and wxPython 2.4.2.1.  It should work
on later versions of Python and wxPython.

#----------------------------------- Help ------------------------------------
The majority of PyPE was written from 10:30PM on the 2nd of July through
10:30PM on the 3rd of July.  Additional features were put together on the 4th
of July along with some bug fixing and more testing.  Truthfully, I've been
using it to edit itself since the morning of the 3rd of July, and believe it
is pretty much feature-complete (in terms of standard Python source editing).
There are a few more things I think it would be nice to have, and they will be
added in good time.

On the most part, this piece of software should work exactly the way you
expect it to.  That is the way I wrote it.  As a result, you don't get much
help in using it (mostly because I am lazy).  When questions are asked, I'll
add the question and answer into the FAQ, which is at the end of this
document.


You'll notice some really useful things, like it remembering which path the
file you have currently open was in (for further opens), or in the case of
new files that have not been saved, the path of the last opened file.  I find
this quite convenient, I hope you do too.


The majority of the things that this editor can do are in the menus.  Hot-keys
for things that have them are listed next to their menu items.  As I am still
learning all the neat things one can do with wxStyledTxtCtrl, I don't know all
the built-in features, and this is likely as much of a learning experience for
me as you.

#-------------------------------- Visual bugs --------------------------------
Save As dialog:
When the Save As dialog opens for you to save a document, rather than 'save',
it lists 'open'.  This is the result of using the standard wxPython browse
dialog, which I use to get a folder and path.  I assure you, it saves your
document properly.

#------------------------------------ FAQ ------------------------------------
Find/Replace dialogs:
One big thing to note is how the find and find/replace dialogs work.  For
those of you who are annoyed with one's normal inability to enter in things
like newlines, this will be a great thing for you.

If you have ' or " as the first character in a find or find/replace dialog,
and what you entered is a proper string declaration in Python, that is the
string that will be found/replaced or replaced with.  Sorry, no raw string
support via r'c:\\new downloads\\readme.txt' so yeah.

As well, I've not implemented the ability to search up in the find dialog.
I may in future versions.  No matter what you have selected, it will always
search forward (and even wrap around if you keep hitting 'find next').

Converting between tabs and spaces:
So, you got tabs and you want spaces, or you have spaces and want to make them
tabs.  As it is not a menu option, you're probably wondering "how in the hell
am I going to do this".  Well, if you read the above stuff about the find and
replace dialogs, it would be trivial.
Both should INCLUDE the quotation marks.
To convert from tabs to 8 spaces per tab; replace "\t" with "        "
To convert from 8 spaces to one tab; replace "        " with "\t"


CRLF/LF/CR line endings:
PyPE will attempt to figure out what kind of file was opened, it does this by
counting the number of different kind of line endings.  Which ever line ending
appears the most in an open file will set the line ending support for viewing
and editing in the window.  Also, any new lines will have that line ending.
New files will have the default line endings as the host operating system, as
given in configuration.py.  The only platforms I don't know for sure are
RISCOS and JAVA, though I assume them to be '\n'.  Any information about what
really is the case would be great.

Additionally, copying from an open document will not change the line-endings.
Future versions of PyPE may support the automatic translation of text during
copying and pasting to the host operating system's native line endings.

Converting between line endings is as easy as the tab and space conversion as
given above.


STCStyleEditor.py:
As I didn't write this, I can offer basically no support for it.  It seems to
work to edit python colorings, and if you edit some of the last 30 or so lines
of it, you can actually use the editor to edit some of the other styles that
are included.

If it just doesn't work for you, I suggest you revert to the copy of the
editor and stc-styles.rc.cfg that is included with the distribution of PyPE
you received.  As it is a known-good version, use it.
#------------------------------- End of file. --------------------------------
