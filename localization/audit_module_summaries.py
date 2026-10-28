#!/usr/bin/env python3
"""Exercise real scoped summary translation and CBR display boundaries."""
import subprocess
import tempfile
from pathlib import Path
from generate import ROOT, catalog, encode, c_string
from c_extract import function

bmp = (ROOT/'src/bmp.c').read_text()
summaries = catalog('module-summary-ru.tsv')
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "menu_ru_data.h"
typedef struct { struct { int charLast; } hdr; char *cTable; } font;
struct { void *bitmap; } font_dynamic[8];
int menu_language_ru=1;
#define FONT_ID(f) (((f)>>16)&7)
#define FONT_CANON (7u<<16)
#define FONT_LARGE (4u<<16)
#define FONT_MED (2u<<16)
'''
for name in ('menu_ru_display', 'bmp_translate_string', 'bmp_translate_module_summary', 'bmp_translate_module_name'):
    code += function(bmp, name)+'\n'
code += '''int main(void) {
font valid={{225},"bitmap"},old={{159},"bitmap"};
for(int i=0;i<8;i++)font_dynamic[i].bitmap=&valid;
'''
for en, ru in summaries.items():
    a,b=c_string(en.encode()),c_string(encode(ru))
    code += f'''{{ const char *s={a};
      for(int language=0;language<2;language++) {{
        menu_language_ru=language;
        const char *expected=language ? {b} : s;
#ifndef CONFIG_MENU_RU
        expected=s;
#endif
        assert(!strcmp(bmp_translate_module_summary(FONT_MED,s),expected));
        assert(bmp_translate_string(FONT_MED,s)==s);
      }}
      menu_language_ru=1;
      for(int id=0;id<8;id++) {{
        if(id>4) assert(bmp_translate_module_summary(id<<16,s)==s);
        font_dynamic[id].bitmap=&old;
        assert(bmp_translate_module_summary(id<<16,s)==s);
        font_dynamic[id].bitmap=0;
        assert(bmp_translate_module_summary(id<<16,s)==s);
        font_dynamic[id].bitmap=&valid;
      }}
    }}\n'''
for en, ru in catalog('module-names-ru.tsv').items():
    a,b=c_string(en.encode()),c_string(encode(ru))
    code += f'''{{ const char *s={a};
      for(int language=0;language<2;language++) {{
        menu_language_ru=language;
        const char *expected=language ? {b} : s;
#ifndef CONFIG_MENU_RU
        expected=s;
#endif
        assert(!strcmp(bmp_translate_module_name(FONT_MED,s),expected));
        assert(bmp_translate_string(FONT_MED,s)==s);
      }}
      menu_language_ru=1;
      for(int id=0;id<8;id++) {{
        if(id>4) assert(bmp_translate_module_name(id<<16,s)==s);
        font_dynamic[id].bitmap=&old;
        assert(bmp_translate_module_name(id<<16,s)==s);
        font_dynamic[id].bitmap=0;
        assert(bmp_translate_module_name(id<<16,s)==s);
        font_dynamic[id].bitmap=&valid;
      }}
    }}\n'''
code += r'''
const char *files[]={"adv_int.mo","lua.mo","dual_iso.mo","ML/modules/file_man.mo"};
for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);i++) {
 assert(bmp_translate_module_name(FONT_MED,files[i])==files[i]);
 assert(bmp_translate_string(FONT_MED,files[i])==files[i]);
}
/* These are module names, also used as Summary in upstream metadata. */
const char *names[]={"Lua scripting","Arkanoid game","Dual ISO","Raw video v1.1 (MLV Lite)"};
for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++)
  assert(bmp_translate_string(FONT_MED,names[i])==names[i]);
const char *unknown="Unknown module %s%n.";
assert(bmp_translate_module_summary(FONT_MED,unknown)==unknown);
for(int factor=1;factor<=30;factor++) {
 char source[32],copy[32],expected[32];
 snprintf(source,sizeof(source),"%s%d.%dx%s",factor>10?"up to ":"",
          factor/10,factor%10,factor==10?" (default)":"");
 strcpy(copy,source);
 for(int language=0;language<2;language++) {
  menu_language_ru=language;
  const char *actual=bmp_translate_string(FONT_MED,source);
  const char *want=source;
#ifdef CONFIG_MENU_RU
  if(language && factor>10) {
   snprintf(expected,sizeof(expected),RU_UP_TO,factor/10,factor%10);want=expected;
  }
  if(language && factor==10)want=RU_DEFAULT;
#else
  (void)expected;
#endif
  assert(!strcmp(actual,want));
  assert(!strcmp(source,copy));
 }
}
puts("PASS: 19 summaries and 19 display names, EN/RU, font fallbacks, unchanged files and 30 CBR values.");
return 0;
}
'''
code=code.replace('RU_UP_TO',c_string(encode('до %d.%dx')))
code=code.replace('RU_DEFAULT',c_string(encode('1.0x (по умолчанию)')))
for config in (False,True):
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'test.c').write_text(code)
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-parameter',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all',
            *(['-DCONFIG_MENU_RU'] if config else []),'-I'+str(ROOT/'src'),
            str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
