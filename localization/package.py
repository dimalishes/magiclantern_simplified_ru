#!/usr/bin/env python3
"""Package a card update, source overlay and checksums without an installer."""
import hashlib
import json
import zipfile
from pathlib import Path
from generate import ROOT, catalog

out=ROOT.parent
staging=ROOT/'platform/5D2.212/build/zip'
assert (staging/'autoexec.bin').is_file()
assert b'RU-alpha1-ed3e7c0' in (staging/'autoexec.bin').read_bytes()
assert (staging/'ML/modules/5D2_212.sym').is_file()
update=out/'magiclantern-5D2.212-RU-alpha1-update.zip'
with zipfile.ZipFile(update,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(staging.rglob('*')):
        if p.is_file() and p.name!='ML-SETUP.FIR' and not {'SETTINGS','LOGS'} & set(p.parts):
            # Upstream make stages static assets only when creating ZIP_DIR;
            # a later font regeneration does not refresh that directory.
            source = ROOT/'data/fonts'/p.name if p.parent==staging/'ML/fonts' and p.suffix=='.rbf' else p
            z.write(source,p.relative_to(staging))
    z.write(ROOT/'localization/README-RU.md','README-RU.md')
    z.write(ROOT/'localization/DejaVu-LICENSE.txt','ML/fonts/DejaVu-LICENSE.txt')
    z.write(ROOT/'COPYING','COPYING')
with zipfile.ZipFile(update) as z:
    assert z.testzip() is None
    assert 'ML-SETUP.FIR' not in z.namelist()
    assert z.read('autoexec.bin')==(staging/'autoexec.bin').read_bytes()
    for p in (ROOT/'data/fonts').glob('*.rbf'):
        assert z.read('ML/fonts/'+p.name)==p.read_bytes()
files=['src/bmp.c','src/menu.c','src/rbf_font.c','src/menu_ru_data.h',
       'platform/5D2.212/internals.h']
files += [str(p.relative_to(ROOT)) for p in (ROOT/'localization').glob('*') if p.is_file()]
files += [str(p.relative_to(ROOT)) for p in (ROOT/'data/fonts').glob('*.rbf')]
changes=out/'magiclantern-RU-alpha1-changes.zip'
with zipfile.ZipFile(changes,'w',zipfile.ZIP_DEFLATED) as z:
    for name in sorted(files):z.write(ROOT/name,name)
manifest={'base_commit':'ed3e7c0dfacfdeaf3349dee73edf9e3621217462',
          'target':'5D2.212','version':'RU-alpha1-ed3e7c0','translations':len(catalog()),
          'compiler':'GNU Arm Embedded 10.3-2021.10',
          'camera_tested':False,'qemu_tested':False,'files':{}}
for p in (update,changes,staging/'autoexec.bin'):
    manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(out/'RU-alpha1-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'README-RU-alpha1.md').write_bytes((ROOT/'localization/README-RU.md').read_bytes())
print(json.dumps(manifest,indent=2))
