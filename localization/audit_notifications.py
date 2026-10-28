#!/usr/bin/env python3
"""Exercise actual NotifyBox formatting/task handoff and multiline catalog text."""
import subprocess
import tempfile
from pathlib import Path
from generate import ROOT, HEADER, c_string, encode, catalog
from c_extract import function

source = (ROOT/'src/notify_box.c').read_text()
entries = catalog()
message = 'Camera was not shut down cleanly.\r\nSkipping module loading.'
assert entries[message] == 'Камера выключена некорректно.\nЗагрузка модулей пропущена.'
assert entries['Saving core dump, please wait...\n'].endswith('\n')
code = r'''
#include <stdio.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#include "menu_ru_data.h"
#define TASK_LOOP for(int once=0;once<1;once++)
#define MAX(a,b) ((a)>(b)?(a):(b))
#define streq(a,b) (!strcmp(a,b))
#define FONT_LARGE 4
#define FONT_MED_LARGE 3
#define FONT_MED 2
#define FONT_ID(f) (f)
struct { void *bitmap; } font_dynamic[8];
static const unsigned char widths[8][256] = { WIDTH_TABLES };
static int notify_box_show_sem,notify_box_main_sem;
static int notify_box_timeout,notify_box_stop_request,notify_box_dirty;
static char notify_box_msg[100],notify_box_msg_tmp[100];
static char printed[128];static int draws,language,last_font;
const char *bmp_translate_dynamic(uint32_t,const char*,char*,size_t);
static int bmp_string_width(int font,const char*s) {
 char display[128];s=bmp_translate_dynamic(font,s,display,sizeof(display));
 if(language)s=menu_ru_lookup(s);
 int line=0,result=0;while(*s){unsigned char c=*s++;if(c=='\n'){result=MAX(result,line);line=0;}else line+=widths[font][c];}
 return MAX(result,line);
}
static int take_semaphore(int sem,int timeout){return 0;}
static void give_semaphore(int sem){}
static void qprint(const char*s){}
static void redraw(void){}
static void msleep(int ms){}
static void bmp_printf(int f,int x,int y,const char*fmt,...) {
 last_font=f;
 assert(!strcmp(fmt,"%s"));
 va_list ap;va_start(ap,fmt);vsnprintf(printed,sizeof(printed),fmt,ap);va_end(ap);
 if(language){char display[128];const char*t=bmp_translate_dynamic(f,printed,display,sizeof(display));if(t!=printed)snprintf(printed,sizeof(printed),"%s",t);}
 draws++;
}
'''
code += '''static const char *bmp_translate_string(uint32_t f,const char *s) {
 return language && font_dynamic[f].bitmap ? menu_ru_lookup(s) : s;
}\n'''
code += '#include "menu_ru_runtime.h"\n'
code += function((ROOT/'src/bmp.c').read_text(),'bmp_translate_dynamic')+'\n'
code += function((ROOT/'src/bmp.c').read_text(),'bmp_translate_config_message')+'\n'
code += function(source,'NotifyBox_task') + '\n'
code += function(source,'NotifyBox') + '\n'
code += r'''
int main(void) {
 for(int f=0;f<8;f++)font_dynamic[f].bitmap=(void*)1;
 const char *messages[]={"100% ready: %s %n",MESSAGE,"Saving core dump, please wait...\n","Unknown message","Config: test%name","Volume: 48 + (0,0) dB","Reversing 3 steps..."};
 const char *translated[]={"100% ready: %s %n",TRANSLATED,EXPECTED_DUMP,"Unknown message",EXPECTED_CONFIG,EXPECTED_VOLUME,EXPECTED_REVERSE};
 for(language=0;language<2;language++)for(int i=0;i<7;i++) {
  NotifyBox(100,"%s",messages[i]);
  assert(!strcmp(notify_box_msg,messages[i]));
  draws=0;NotifyBox_task(0);assert(draws==2);
  assert(!strcmp(printed,language?translated[i]:messages[i]));
 }
 char long_message[256];memset(long_message,'x',sizeof(long_message)-1);long_message[255]=0;
 NotifyBox(100,"%s",long_message);assert(strlen(notify_box_msg)==98);
 draws=0;NotifyBox_task(0);assert(draws==2 && strlen(printed)==98);
 language=1;
 NotifyBox(100,"%s","Pls send COREDUMP.DAT to ML devs.\n");NotifyBox_task(0);
 assert(bmp_string_width(FONT_LARGE,"Pls send COREDUMP.DAT to ML devs.\n")>670);
 assert(last_font==FONT_MED_LARGE && bmp_string_width(last_font,"Pls send COREDUMP.DAT to ML devs.\n")<=670);
 for(int f=0;f<8;f++)font_dynamic[f].bitmap=0;
 NotifyBox(100,"%s",long_message);NotifyBox_task(0);assert(last_font==FONT_LARGE);
 puts("PASS: actual NotifyBox/task formatting, literal percents, EN/RU multiline text, CRLF and truncation.");
 return 0;
}
'''
code = code.replace('MESSAGE', c_string(message.encode()))
code = code.replace('TRANSLATED', c_string(encode(entries[message])))
code = code.replace('EXPECTED_DUMP', c_string(encode(entries['Saving core dump, please wait...\n'])))
code = code.replace('EXPECTED_CONFIG', c_string(encode('Конфиг: test%name')))
code = code.replace('EXPECTED_VOLUME', c_string(encode('Громкость: 48 + (0,0) дБ')))
code = code.replace('EXPECTED_REVERSE', c_string(encode('Обратный ход: 3 шагов...')))
tables=[]
for index,name in [(2,'argnor23.rbf'),(3,'argnor28.rbf'),(4,'argnor32.rbf')]:
    data=(ROOT/'data/fonts'/name).read_bytes();h=HEADER.unpack_from(data)
    widths=[0]*256;widths[h[7]:h[8]+1]=data[h[10]:h[10]+h[8]-h[7]+1]
    tables.append('['+str(index)+']={'+','.join(map(str,widths))+'}')
code=code.replace('WIDTH_TABLES',','.join(tables))
with tempfile.TemporaryDirectory() as folder:
    p=Path(folder);(p/'test.c').write_text(code)
    subprocess.run(['gcc','-std=c99','-DCONFIG_MENU_RU','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                    '-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
