#!/usr/bin/env python3
"""Test real finite display composition, preserved arguments and font/buffer gates."""
from pathlib import Path
import json,re,subprocess,tempfile,itertools
from generate import ROOT,c_string,encode,catalog
from c_extract import function
bmp=(ROOT/'src/bmp.c').read_text()
code=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "menu_ru_data.h"
typedef struct {struct {int charLast;} hdr;char *cTable;} font;
struct {void *bitmap;} font_dynamic[8];int menu_language_ru=1;
#define FONT_ID(f) (((f)>>16)&7)
#define FONT_CANON (7u<<16)
#define FONT_LARGE (4u<<16)
#define FONT_MED (2u<<16)
'''
code+=function(bmp,'menu_ru_display')+'\n'+function(bmp,'bmp_translate_string')+'\n'
code+='#ifdef CONFIG_MENU_RU\n#include "menu_ru_runtime.h"\n#endif\n'
code+=function(bmp,'bmp_translate_dynamic')+'\n'
patterns=json.loads((ROOT/'localization/final-runtime-patterns.json').read_text())
tokens=re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[dsxX]|%)')
cases=[]
for p in patterns:
    if p['id']==3030:continue
    specs=[m[0] for m in tokens.finditer(p['en']) if m[0]!='%%']
    for number in [0,42,-42,2147483647]:
        args=[]
        for i,s in enumerate(specs):
            if s.endswith('s'):
                args.append('' if 1676<=p['id']<=1685 else 'path%name%s%n')
            else:args.append((number & 0xffffffff) if s[-1] in 'xX' else number)
        source=p['en']%tuple(args);expected=p['ru']%tuple(args)
        if len(source.encode('latin1'))>127 or len(encode(expected))>=128:continue
        cases.append((p['id'],source,expected))
# All 720 valid Magic Zoom box combinations, plus fullscreen.
for a,ar in [('HalfS, ','Полунаж., '),('Focus, ','Кольцо, '),('F+HS, ','Кольцо+полунаж., '),('ALW, ','Всегда, ')]:
    cases.append((4000,a+'FullScreen',ar+'На весь экран'))
    for b,br in [('Small, ','Мал., '),('Med, ','Сред., '),('Large, ','Бол., ')]:
        for c,cr in [('AFbox, ','Рамка AF, '),('TL, ','ВЛ, '),('TR, ','ВП, '),('BR, ','НП, '),('BL, ','НЛ, ')]:
            for scale in ['1:1','2:1','3:1','4:1']:
                for d,dr in [('', ''),(', Ss',', РЭ'),(', Sz',', SS ZeroCross')]:
                    cases.append((4000,a+b+c+scale+d,ar+br+cr+scale+dr))
extras=[
('Microphone connected','Микрофон: есть'),('Headphones disconnected','Наушники: нет'),
('FW default(reboot)','Штатный(перезапуск)'),
('ON, 30s','ВКЛ, 30 с'),('5 steps from here','5 шагов от текущей точки'),
('DOF Far:     Infty','ГРИП до:  беск.'),
('Focus dist:  Infty','Дист. фокуса:  беск.'),
('DOF Far:    myfile%name','ГРИП до: myfile%name'),
('0h00m10s','0 ч 00 мин 10 с'),('01m10s','01 мин 10 с'),
('ON, 1h02m03s','ВКЛ, 1 ч 02 мин 03 с'),('ON, 3m','ВКЛ, 3 мин'),
('1h2m','1 ч 2 мин'),('1h3s','1 ч 3 с'),('after 10sec','через 10 с'),
('20 ms','20 мс'),('20 \x84s','20 мкс'),
('+42 steps from here','+42 шагов от текущей точки'),('0 (here)','0 (здесь)'),
('Focus stack: 3...','Focus Stacking: 3...'),
('LCD Saturation  : High','Насыщенность LCD: Высокая'),
('R multiplier','Множитель R'),('Blue 4','Синий 4'),
('Handhedld MLU does not work with intervalometer.','Предподъём с рук не работает вместе с интервалометром.'),
('Handhedld MLU does not work with motion detection.','Предподъём с рук не работает вместе с детектором движения.'),
('Clip warning  : 0.01% px','Пересвет: 0.01% пикс.'),
('8 frames unnecessary and may cause excessive shutter wear.','8 кадров не требуется и может ускорить износ затвора.'),
('Load failed: file%name.mo, ret 0xFF. Press PicStyle for more info.','Сбой загрузки: file%name.mo, код 0xFF. Подробнее: нажмите PicStyle.'),
('Module not loaded. Press PicStyle for more info.','Модуль не загружен. Подробнее: нажмите PicStyle.'),
('64K, 16K used','64K, занято 16K'),('64K of 128K','64K из 128K'),
('[FAIL] 16K','[ОШИБКА] 16K'),('64K, peak 128K','64K, пик 128K'),('src/file%name.c:42 task menu','src/file%name.c:42 задача menu'),
('ID error,double free','ошибка ID,повторное освобождение'),
('ID error[1/2] malloc(16K) at src/file.c:42, task menu.','ошибка ID[1/2] malloc(16K), src/file.c:42, задача menu.'),
('Will use RAW RGB zebras in LiveView and after taking a pic.','RAW RGB-зебра в LiveView и после снимка.'),
('Will use RAW RGB zebras after taking a pic.','RAW RGB-зебра после снимка.'),
]
cases.extend((5000,a,b) for a,b in extras)
warning_pairs=[('Mode is not M','Режим отличается от M'),('Pic quality is not RAW','Качество снимков отличается от RAW'),('ALO is enabled','ALO включён'),("WB isn't set to auto",'Баланс белого не автоматический'),('Focus is not manual','Фокус не ручной')]
for count in range(1,6):
 for sep in ['\n',', ']:
  cases.append((6000,sep.join(a for a,b in warning_pairs[:count])+sep,sep.join(b for a,b in warning_pairs[:count])+sep))
# Literal data can contain printf-looking bytes; they must be copied verbatim.
cases.extend([(7000,'File%sn not found','File%sn не найден'),(7000,"Missing%s%n not loaded","Missing%s%n не загружен")])
entries=catalog()
cases=[(i,a,entries.get(a,b)) for i,a,b in cases]
code+='struct test {int id;const char *en,*ru;} tests[]={\n'
code+=',\n'.join('{%d,%s,%s}'%(i,c_string(a.encode('latin1')),c_string(encode(b))) for i,a,b in cases)+'};\n'
code+=r'''
int main(void){font valid={{225},"bitmap"},old={{159},"bitmap"},null_table={{225},0};
for(int i=0;i<8;i++)font_dynamic[i].bitmap=&valid;
unsigned long checks=0;
for(unsigned t=0;t<sizeof(tests)/sizeof(tests[0]);t++){
 struct test v=tests[t];char original[128];strcpy(original,v.en);
 for(int lang=0;lang<2;lang++)for(int id=0;id<8;id++)for(int state=0;state<4;state++){
  menu_language_ru=lang;font_dynamic[id].bitmap=state==0?&valid:state==1?&old:state==2?&null_table:0;
  unsigned char memory[160];memset(memory,0xa5,sizeof(memory));
  const char *result=bmp_translate_dynamic(id<<16,original,(char*)memory+8,128);
  const char *expected=original;
#ifdef CONFIG_MENU_RU
  if(lang && id<=4 && state==0)expected=v.ru;
#endif
  if(strcmp(result,expected)){fprintf(stderr,"FAIL template %d: %s (lang=%d font=%d state=%d)\n",v.id,v.en,lang,id,state);return 1;}
  assert(!strcmp(original,v.en));for(int i=0;i<8;i++)assert(memory[i]==0xa5);
  for(int i=136;i<160;i++)assert(memory[i]==0xa5);
  font_dynamic[id].bitmap=&valid;checks++;
 }
 menu_language_ru=1;
 for(size_t cap=0;cap<=strlen(v.ru)+1;cap++){
  unsigned char memory[160];memset(memory,0xa5,sizeof(memory));
  const char *result=bmp_translate_dynamic(FONT_MED,original,(char*)memory+8,cap);
  const char *expected=original;
#ifdef CONFIG_MENU_RU
  if(cap>strlen(v.ru))expected=v.ru;
#endif
  if(strcmp(result,expected)){fprintf(stderr,"FAIL capacity %zu template %d: %s\n",cap,v.id,v.en);return 1;}
  for(int i=0;i<8;i++)assert(memory[i]==0xa5);
  for(size_t i=8+cap;i<160;i++)assert(memory[i]==0xa5);
  checks++;
 }
 assert(bmp_translate_dynamic(FONT_MED,original,0,128)==original);
}
menu_language_ru=1;
char overlap[128]="Volume: 42 + (0,0) dB",unchanged[128];strcpy(unchanged,overlap);
assert(bmp_translate_dynamic(FONT_MED,overlap,overlap,sizeof(overlap))==overlap);
assert(!strcmp(overlap,unchanged));
assert(bmp_translate_dynamic(FONT_MED,overlap,overlap+3,100)==overlap);
assert(!strcmp(overlap,unchanged));
const char *unknown[]={"", "Unknown message %s%n", "Volume: NaN dB", "HalfS, Small, XX, 1:1", "ALW, FullScreen extra", "Mode is not M malicious", "Luma unknown", "12345678901234567890 shots"};
for(unsigned i=0;i<sizeof(unknown)/sizeof(unknown[0]);i++){
 char buf[128];if(bmp_translate_dynamic(FONT_MED,unknown[i],buf,sizeof(buf))!=unknown[i]){fprintf(stderr,"Unexpected match: %s\n",unknown[i]);return 1;}}
char too_long[256];memset(too_long,'x',255);too_long[255]=0;
assert(bmp_translate_dynamic(FONT_MED,too_long,(char[128]){0},128)==too_long);
/* Repeated separators exercise the finite match budget and capture backtracking. */
for(unsigned seed=0;seed<2000;seed++){
 char original[128],before[128],out[128];unsigned state=seed+1;
 for(unsigned i=0;i<127;i++){state=state*1664525+1013904223;original[i]="ab. ,%n/09()"[(state>>16)%11];}
 original[seed%128]=0;strcpy(before,original);
 const char *result=bmp_translate_dynamic(FONT_MED,original,out,sizeof(out));
 assert(!strcmp(original,before));assert(strlen(result)<128);checks++;
}
printf("PASS: %zu display cases, %lu language/font/buffer/fuzz checks; ASan+UBSan.\n",sizeof(tests)/sizeof(tests[0]),checks);
return 0;}
'''
(ROOT.parent/'audit/final-runtime-test.c').write_text(code)
for config in (False,True):
 with tempfile.TemporaryDirectory() as folder:
  p=Path(folder);(p/'test.c').write_text(code)
  subprocess.run(['gcc','-std=c99','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter',
   '-fsanitize=address,undefined','-fno-sanitize-recover=all',*(['-DCONFIG_MENU_RU'] if config else []),
   '-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
  subprocess.run([str(p/'test')],check=True)
