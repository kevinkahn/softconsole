from datetime import datetime

committime = datetime.now().strftime("%c")
with open('gitver.py', 'r') as gitver:
	lines = gitver.readlines()
	print(lines)
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
		print('Skip nl')
		pass
	else:
		newlines.append(line)
print(lines)
with open('gitver.py', 'w') as gitver:
	for line in newlines:
		print(line)
		print(line, file=gitver)
