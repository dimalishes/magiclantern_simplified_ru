#!/usr/bin/env python3
"""Exercise actual menu text composition with language and font fallbacks."""
import subprocess
import tempfile
from pathlib import Path
from generate import ROOT, encode, c_string
from c_extract import function

bmp = (ROOT/'src/bmp.c').read_text()
menu = (ROOT/'src/menu.c').read_text()
code = r'''
#include <stdint.h>
#include <stddef.h>
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
#define MENU_MAX_WARNING_LEN 100
struct menu_entry { int min,max; const char **choices; };
'''
code += function(bmp, 'menu_ru_display') + '\n'
code += function(bmp, 'bmp_translate_string') + '\n'
# Only the line-length cutoff needs a width here; rendering has a separate audit.
code += 'static int bmp_string_width(int f,const char*s){return 8*strlen(bmp_translate_string(f,s));}\n'
for name in ('pickbox_string', 'menu_parent_disabled_warning', 'menu_build_choice_help'):
    code += function(menu, name) + '\n'

def literal(text):
    return c_string(encode(text))

code += r'''
int main(void) {
 font valid={{225},"bitmap"},old={{159},"bitmap"};
 for(int i=0;i<8;i++)font_dynamic[i].bitmap=&valid;
 const char *choices[]={"OFF","Exposure Fusion","Timelapse Play"};
 struct menu_entry entry={0,2,choices};char text[256],warning[100];
 const char *english="OFF / Exposure Fusion / Timelapse Play.";
 const char *ru_choices=RU_CHOICES;
 const char *ru_warning=RU_WARNING;
 menu_language_ru=0;
 menu_build_choice_help(&entry,text,sizeof(text));assert(strcmp(text,english)==0);
 menu_parent_disabled_warning(warning,"REC key");assert(strcmp(warning,"REC key is disabled.")==0);
 menu_parent_disabled_warning(warning,"Zebras");assert(strcmp(warning,"Zebras are disabled.")==0);
 menu_language_ru=1;
 menu_build_choice_help(&entry,text,sizeof(text));assert(strcmp(text,ru_choices)==0);
 menu_parent_disabled_warning(warning,"REC key");assert(strcmp(warning,ru_warning)==0);
 menu_parent_disabled_warning(warning,"Magic Zoom");
 assert(strcmp(warning,"Magic Zoom is disabled.")==0);
#ifdef CONFIG_MENU_RU
 assert(strcmp(bmp_translate_string(FONT_MED,warning),RU_MAGIC)==0);
 menu_parent_disabled_warning(warning,"unknown%n");assert(strcmp(warning,RU_UNKNOWN)==0);
#else
 menu_parent_disabled_warning(warning,"unknown%n");assert(strcmp(warning,"unknown%n is disabled.")==0);
#endif
 const char *name="REC key";
 assert(bmp_translate_string(FONT_CANON,name)==name);
 assert(bmp_translate_string(5u<<16,name)==name);
 font_dynamic[2].bitmap=&old;
 menu_build_choice_help(&entry,text,sizeof(text));assert(strcmp(text,english)==0);
 menu_parent_disabled_warning(warning,name);assert(strcmp(warning,"REC key is disabled.")==0);
 font_dynamic[2].bitmap=0;
 menu_build_choice_help(&entry,text,sizeof(text));assert(strcmp(text,english)==0);
 font_dynamic[2].bitmap=&valid;
 const char *percent[]={"100%","%s","%n"};entry.choices=percent;
 menu_build_choice_help(&entry,text,sizeof(text));assert(strcmp(text,"100% / %s / %n.")==0);
 /* Every small destination size, including zero: no writes outside bounds. */
 for(int language=0;language<2;language++)for(size_t capacity=0;capacity<=64;capacity++) {
  unsigned char memory[96];memset(memory,0xA5,sizeof(memory));
  menu_language_ru=language;entry.choices=choices;
  menu_build_choice_help(&entry,(char*)memory+8,capacity);
  for(int i=0;i<8;i++)assert(memory[i]==0xA5);
  for(size_t i=8+capacity;i<sizeof(memory);i++)assert(memory[i]==0xA5);
  if(capacity)assert(strlen((char*)memory+8)<capacity);
 }
 puts("PASS: real menu composition, EN/RU, old/missing/custom/Canon fonts, percent literals and 130 bounded-buffer cases.");
 return 0;
}
'''
code = code.replace('RU_MAGIC', literal('Magic Zoom выключен.'))
code = code.replace('RU_UNKNOWN', literal('Отключено: unknown%n.'))
for config in (False, True):
    test = code.replace('RU_CHOICES', literal('ВЫКЛ / Слияние экспозиций / Просмотр таймлапса.') if config else 'english')
    test = test.replace('RU_WARNING', literal('Отключено: Кнопка REC.') if config else '"REC key is disabled."')
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'test.c').write_text(test)
        flags=['-DCONFIG_MENU_RU'] if config else []
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',
                        '-Wno-unused-function','-Wno-unused-parameter',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        *flags,'-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
