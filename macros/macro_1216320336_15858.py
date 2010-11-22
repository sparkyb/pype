
creation_date = 'Thu Jul 17 11:45:36 2008'
name = 'strip trailing whitespace'
hotkeydisplay = ""
hotkeyaccept = ""

def macro(self):
    for i,line in enumerate((self.lines)):
		line_no_le = line.rstrip('\r\n')
		line_no_space = line.rstrip()
		if line_no_le != line_no_space:
			self.lines[i] = line_no_space + line[len(line_no_le)-len(line):]
