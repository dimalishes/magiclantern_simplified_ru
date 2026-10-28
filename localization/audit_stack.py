#!/usr/bin/env python3
"""Compare ARM stack frames using the actual baseline build command."""
import json,shlex,subprocess,tarfile,zipfile
from pathlib import Path
from generate import ROOT
out=ROOT.parent/'audit';out.mkdir(exist_ok=True)
with tarfile.open(ROOT.parent/'magiclantern-ed3e7c0.tar.gz') as t:
    prefix=t.getnames()[0]
    (out/'bmp-baseline.c').write_bytes(t.extractfile(prefix+'/src/bmp.c').read())
with zipfile.ZipFile(ROOT.parent/'magiclantern-RU-alpha1-changes.zip') as z:
    (out/'bmp-alpha1.c').write_bytes(z.read('src/bmp.c'))
lines=(ROOT.parent/'build-baseline.log').read_text().splitlines()
line=next(x for x in lines if ' -o build/bmp.o ' in x and 'arm-none-eabi-gcc' in x)
base=shlex.split(line)
# Remove generated dependency options so this audit cannot replace real .d files.
base=[x for x in base if not x.startswith('-Wp,') and x not in ('-MP','-MD')]
report={}
for mode,source in [('baseline',out/'bmp-baseline.c'),('alpha1',out/'bmp-alpha1.c'),('revised',ROOT/'src/bmp.c')]:
    args=base[:]
    args[args.index('-o')+1]=str(out/('bmp-'+mode+'.o'))
    args[args.index('-c')+args[args.index('-c'):].index('../../src/bmp.c')]=str(source)
    args+=['-fstack-usage']
    result=subprocess.run(args,cwd=ROOT/'platform/5D2.212',capture_output=True,text=True)
    (out/('stack-build-'+mode+'.log')).write_text(result.stdout+result.stderr)
    result.check_returncode()
    entries={}
    for x in (out/('bmp-'+mode+'.su')).read_text().splitlines():
        fields=x.split('\t'); name=fields[0].rsplit(':',1)[-1]
        if name in ('bmp_puts','bmp_printf','big_bmp_printf','menu_ru_draw','menu_ru_display','bmp_string_width'):
            entries[name]={'bytes':int(fields[1]),'type':fields[2]}
    report[mode]=entries
(out/'arm-stack-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
