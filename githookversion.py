from datetime import datetime

committime = datetime.now().strftime("%c")
with open('gitver.py', 'r') as gitver:
	lines = gitver.readlines()
newlines = []
for line in lines:
	if line.strip().startswith('commitseq'):
		linshr = line.replace(' ', '')
		seq = int(line.strip().split(' =')[1])
		print(seq + 1)
		newlines.append(f"commitseq = {seq + 1}")
	elif line.strip().startswith('committime'):
		newlines.append(f'committime = \"{committime}\"')
	elif line == '\n':
		pass
	else:
		newlines.append(line)
with open('gitver.py', 'w') as gitver:
	for line in newlines:
		print(line, file=gitver)
with open('requirements.txt', 'r') as rqmts:
	lines = rqmts.readlines()
	versline = f'#{committime}/{seq}\n'
	if lines[0].startswith('#'):
		lines[0] = versline
	else:
		lines.insert(0, versline)
with open('requirements.txt', 'w') as rqmts:
	for line in lines:
		rqmts.write(line)
