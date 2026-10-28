#!/usr/bin/env python3
"""Record actual ARM stack frames using the current target build flags."""
import json,subprocess,shlex
from pathlib import Path
from generate import ROOT
base=ROOT.parent;platform=ROOT/'platform/5D2.212';report={}
for source in ['bmp','menu','notify_box','rbf_font']:
 result=subprocess.run(['make','-n','-B','-C',str(platform),'CROSS_COMPILE='+str(base/'gcc-arm-none-eabi-10.3-2021.10/bin/arm-none-eabi-'),'VERSION=RU-alpha2-font1-ed3e7c0','build/'+source+'.o'],text=True,capture_output=True,check=True)
 command=next(x for x in result.stdout.splitlines() if 'arm-none-eabi-gcc ' in x and '-o build/'+source+'.o ' in x)
 args=shlex.split(command);args=[x for x in args if not x.startswith('-Wp,') and x not in ['-MP','-MD']]
 target=base/'audit'/('final-stack-'+source+'.o');args[args.index('-o')+1]=str(target)
 args+=['-fstack-usage']
 result=subprocess.run(args,cwd=platform,capture_output=True,text=True)
 (base/'audit'/('final-stack-'+source+'.log')).write_text(result.stdout+result.stderr);result.check_returncode()
 entries={}
 for line in target.with_suffix('.su').read_text().splitlines():
  fields=line.split('\t');name=fields[0].rsplit(':',1)[-1]
  if int(fields[1])>=128 or 'menu_ru_' in name or name in ['bmp_puts','bmp_printf','bmp_string_width','NotifyBox_task']:
   entries[name]={'bytes':int(fields[1]),'type':fields[2]}
 report[source]=entries
(base/'audit/final-arm-stack.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
