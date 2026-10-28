#!/usr/bin/env python3
"""Exercise the actual scoped choice composer across valid values and fallbacks."""
import subprocess,tempfile
from pathlib import Path
from generate import ROOT,encode,c_string
from c_extract import function
bmp=(ROOT/'src/bmp.c').read_text()
code=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "menu_ru_data.h"
typedef struct { struct { int charLast; } hdr; char *cTable; } font;
struct {void *bitmap;} font_dynamic[8];
int menu_language_ru=1;
#define FONT_ID(f) (((f)>>16)&7)
#define FONT_CANON (7u<<16)
#define FONT_LARGE (4u<<16)
'''
for name in ('menu_ru_display','bmp_translate_string','menu_ru_value_number','bmp_translate_menu_value'):
    code+=function(bmp,name)+'\n'
cases=[]
for cs,ru in [('Luma','Яркость'),('RGB','RGB'),('LumaFast','Яркость (быстро)')]:
    for hi in range(70,101):cases.append(('Zebras',f'{cs}, over {hi}%',f'{ru}, выше {hi}%'))
    for lo in range(1,21):
        cases.append(('Zebras',f'{cs}, under {lo}%',f'{ru}, ниже {lo}%'))
        for hi in range(70,101):cases.append(('Zebras',f'{cs}, {lo}..{hi}%',f'{ru}, {lo}..{hi}%'))
for thr in range(1,51):
    for color in ['R','G','B','C','M','Y','global','local']:
        for gray in ['',',Gray']:
            cases.append(('Focus Peak',f'ON,{thr//10}.{thr%10},{color}{gray}',
                f'ВКЛ,{thr//10}.{thr%10},'+{'global':'общий','local':'локальный'}.get(color,color)+(',ЧБ' if gray else '')))
for unit,ru in [('Percent','Проценты'),('0..255','0..255'),('RGB','RGB'),('RAW','RAW'),('Percent RGB','Проценты RGB')]:
    for suffix in ['',', AFbox']:cases.append(('Spotmeter',unit+suffix,ru+(', рамка AF' if suffix else '')))
for typ,ru in [('Luma (YUV)','Яркость (YUV)'),('RGB (YUV)','RGB (YUV)'),('RAW N/A','RAW недоступен'),('RAW RGB','RAW RGB'),('RAW HistoBar','RAW HistoBar')]:
    for suffix,tr in [(', Linear',', линейный'),(', Log',', логарифм.')]:cases.append(('Histogram',typ+suffix,ru+tr))
cases.append(('Histogram','RAW HistoBar','RAW HistoBar'))
code+='struct test {const char *name,*en,*ru;} tests[]={\n'
code+=',\n'.join('{'+','.join([c_string(n.encode()),c_string(en.encode()),c_string(encode(ru))])+'}' for n,en,ru in cases)+'};\n'
code+=r'''
int main(void){font valid={{225},"bitmap"},old={{159},"bitmap"};
for(int i=0;i<8;i++)font_dynamic[i].bitmap=&valid;
for(unsigned t=0;t<sizeof(tests)/sizeof(tests[0]);t++){
 struct test v=tests[t]; char original[128];strcpy(original,v.en);
 for(int language=0;language<2;language++)for(int id=0;id<8;id++)for(int state=0;state<3;state++){
  menu_language_ru=language;font_dynamic[id].bitmap=state==0?&valid:state==1?&old:0;
  unsigned char memory[160];memset(memory,0xa5,sizeof(memory));
  const char *out=bmp_translate_menu_value(id<<16,v.name,original,(char*)memory+8,128);
  const char *expected=original;
#ifdef CONFIG_MENU_RU
  if(language && id<=4 && state==0)expected=v.ru;
#endif
  if(strcmp(out,expected)){fprintf(stderr,"Failed %s %s id %d state %d\n",v.name,v.en,id,state);return 1;}
  assert(!strcmp(original,v.en));
  for(int i=0;i<8;i++)assert(memory[i]==0xa5);
  for(int i=136;i<160;i++)assert(memory[i]==0xa5);
  font_dynamic[id].bitmap=&valid;
 }
 menu_language_ru=1;
 for(size_t cap=0;cap<=strlen(v.ru)+1;cap++){
  unsigned char memory[160];memset(memory,0xa5,sizeof(memory));
  const char *out=bmp_translate_menu_value(2u<<16,v.name,original,(char*)memory+8,cap);
#ifdef CONFIG_MENU_RU
  assert(!strcmp(out,cap>strlen(v.ru)?v.ru:original));
#else
  assert(out==original);
#endif
  for(int i=0;i<8;i++)assert(memory[i]==0xa5);
  for(size_t i=8+cap;i<160;i++)assert(memory[i]==0xa5);
 }
 assert(bmp_translate_menu_value(2u<<16,v.name,original,0,128)==original);
 assert(bmp_translate_menu_value(2u<<16,"Other",original,(char[128]){0},128)==original);
}
const char *bad[]={"", "ON,0.0,local", "ON,5.1,R", "ON,1.0,%n", "ON,1.0,local,Gray%n",
"Luma, over 101%", "Luma, under 21%", "Luma, 1..69%", "RGB, 99999999999999..100%",
"RAW N/A, Log%n", "Percent, AFbox, AFbox", "ON,1", "ON,1.", "ON,1.0", "ON,1.0,"};
const char *names[]={"Zebras","Focus Peak","Spotmeter","Histogram"};
for(unsigned n=0;n<4;n++)for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
 char buf[128];assert(bmp_translate_menu_value(2u<<16,names[n],bad[i],buf,sizeof(buf))==bad[i]);}
printf("PASS: %zu valid values, all languages/fonts, bounded buffers, malformed strings, unchanged inputs.\n",sizeof(tests)/sizeof(tests[0]));
return 0;}
'''
for enabled in (False,True):
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'test.c').write_text(code)
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all',*(['-DCONFIG_MENU_RU'] if enabled else []),
            '-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
