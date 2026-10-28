#!/usr/bin/env python3
"""Test the real config display matcher, font gates and bounded formatting."""
import subprocess
import tempfile
from pathlib import Path
from generate import ROOT, encode, c_string
from c_extract import function

bmp=(ROOT/'src/bmp.c').read_text()
code=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "menu_ru_data.h"
typedef struct { struct { int charLast; } hdr; char *cTable; } font;
struct { void *bitmap; } font_dynamic[8];
int menu_language_ru=1;
#define FONT_ID(f) (((f)>>16)&7)
#define FONT_CANON (7u<<16)
#define FONT_LARGE (4u<<16)
#define FONT_MED (2u<<16)
'''
for name in ('menu_ru_display','bmp_translate_string','bmp_translate_config_message'):
    code+=function(bmp,name)+'\n'
code+='int main(void) { font valid={{225},"bitmap"},old={{159},"bitmap"};\n'
code+='for(int i=0;i<8;i++)font_dynamic[i].bitmap=&valid;\n'
cases=[
 ('Only the current preset: ML/SETTINGS/100%s%n/', 'Только текущий конфиг: ML/SETTINGS/100%s%n/'),
 ('Config: test%s%n', 'Конфиг: test%s%n'),
 ('Config: ', 'Конфиг: '),
 ('Restart to load the config for Av mode.', 'Перезапустите камеру для загрузки конфига режима Av.'),
 ('Camera was started in M; restart to load the config for C1.', 'При включении: M. Для конфига C1 перезапустите камеру.'),
 ('Camera was started in %s; restart to load the config for %n.', 'При включении: %s. Для конфига %n перезапустите камеру.'),
]
for source,translation in cases:
    code+=f'''{{char original[256]={c_string(source.encode())},before[256];
    strcpy(before,original); const char *ru={c_string(encode(translation))};
    for(int language=0;language<2;language++)for(int id=0;id<8;id++)
    for(int state=0;state<3;state++)for(size_t capacity=0;capacity<=128;capacity++) {{
      unsigned char memory[160]; memset(memory,0xa5,sizeof(memory));
      menu_language_ru=language;
      font_dynamic[id].bitmap=state==0?&valid:state==1?&old:0;
      const char *result=bmp_translate_config_message(id<<16,original,(char*)memory+8,capacity);
      const char *expected=original;
#ifdef CONFIG_MENU_RU
      if(language && id<=4 && state==0 && capacity>strlen(ru))expected=ru;
#endif
      assert(!strcmp(result,expected));assert(!strcmp(original,before));
      for(unsigned i=0;i<8;i++)assert(memory[i]==0xa5);
      for(size_t i=8+capacity;i<sizeof(memory);i++)assert(memory[i]==0xa5);
      if(result!=original)assert(strlen(result)<capacity);
      font_dynamic[id].bitmap=&valid;
    }}
    assert(bmp_translate_config_message(FONT_MED,original,0,128)==original);
    (void)ru;
    }}\n'''
code+=r'''
menu_language_ru=1;char buffer[128];
const char *unknown[]={"", "Config", "Config:test", "Other Config: M", "Only the current preset", 
 "Restart to load the config for 123456789 mode.",
 "Restart to load the config for M mode", "Restart to load the config for  mode.",
 "Camera was started in M; restart to load the config for .",
 "Camera was started in ; restart to load the config for M.",
 "Camera was started in M; restart to load the config for M",
 "Camera was started in 123456789; restart to load the config for M."};
for(unsigned i=0;i<sizeof(unknown)/sizeof(unknown[0]);i++)
 assert(bmp_translate_config_message(FONT_MED,unknown[i],buffer,sizeof(buffer))==unknown[i]);
char long_name[256]="Config: ";memset(long_name+8,'x',240);long_name[248]=0;
assert(bmp_translate_config_message(FONT_MED,long_name,buffer,sizeof(buffer))==long_name);
puts("PASS: actual config display matcher, four templates, EN/RU, font fallbacks, literal %s/%n, 37152 bounded cases.");
return 0;}
'''
for config in (False,True):
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'test.c').write_text(code)
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-parameter',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all',
            *(['-DCONFIG_MENU_RU'] if config else []),'-I'+str(ROOT/'src'),
            str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
