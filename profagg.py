#!/usr/bin/env python3
"""Aggregate pcprof.txt ("count hexaddr") through addr2line -i: per top-level voice function
(the outermost Voice/Impl frame, so inlined helpers count towards their caller) and per line.
usage: profagg.py BINARY PCPROF [nfuncs] [nlines]"""
import subprocess, sys, collections
binary, prof = sys.argv[1], sys.argv[2]
nf = int(sys.argv[3]) if len(sys.argv) > 3 else 15
nl = int(sys.argv[4]) if len(sys.argv) > 4 else 30
only = sys.argv[5] if len(sys.argv) > 5 else None  # restrict the line table to one outermost function
rows = [l.split() for l in open(prof)]
addrs = [a for _, a in rows]
out = subprocess.run(['arm-linux-gnueabihf-addr2line', '-i', '-f', '-C', '-a', '-e', binary] + addrs,
                     capture_output=True, text=True).stdout.split('\n')
chains, cur = {}, None
for line in out:
	if line.startswith('0x'):
		cur = int(line, 16)
		chains[cur] = []
	elif cur is not None and line:
		chains[cur].append(line)
byf, byl = collections.Counter(), collections.Counter()
total = 0
for c, a in rows:
	c = int(c)
	total += c
	ch = chains.get(int(a, 16), [])
	frames = [(ch[i], ch[i + 1]) for i in range(0, len(ch) - 1, 2)]  # (function, file:line), innermost first
	top = next((f for f, _ in reversed(frames) if 'Impl::' in f), None) or next((f for f, _ in reversed(frames) if 'Voice::' in f or 'Decimator' in f), None) or (frames[0][0] if frames else '??')
	byf[top.split('(')[0]] += c
	if frames and (only is None or only in top):
		# the line in the outermost voice function (where the inlined call sits) and the innermost
		outer = next((l for f, l in reversed(frames) if top.split('(')[0] in f), frames[0][1])
		byl[outer.split('/')[-1].split(' ')[0] + ' <- ' + frames[0][0].split('(')[0][-30:]] += c
print(f'== by outermost voice function ({total} samples)')
for k, v in byf.most_common(nf):
	print(f'{100 * v / total:5.1f}% {k}')
print('== by line (innermost)')
for k, v in byl.most_common(nl):
	print(f'{100 * v / total:5.1f}% {k}')
