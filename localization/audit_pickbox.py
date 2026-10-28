#!/usr/bin/env python3
"""Check real menu pickbox layout and literal percent output with shipped widths."""
import subprocess
import tempfile
from pathlib import Path
from generate import ROOT, HEADER, c_string
from c_extract import function

menu = (ROOT / 'src/menu.c').read_text()
data = (ROOT / 'data/fonts/argnor32.rbf').read_bytes()
h = HEADER.unpack_from(data)
widths = [0] * 256
widths[h[7]:h[8]+1] = data[h[10]:h[10]+h[8]-h[7]+1]
code = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "menu_ru_data.h"
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define FONT_LARGE 4
#define COLOR_WHITE 1
#define COLOR_BLACK 0
#define MENU_BAR_COLOR 2
#define FONT(a,b,c) (a)
#define SHADOW_FONT(a) (a)
struct menu_entry { int min,max; int *priv; const char **choices; };
#define SELECTED_INDEX(e) (*(e)->priv - (e)->min)
static int language, drawn, box_left, box_right, last_width;
static unsigned char widths[256] = { WIDTHS };
static int bmp_string_width(int f, const char *s) {
 (void)f; if(language)s=menu_ru_lookup(s);
 int w=0; while(*s)w+=widths[(unsigned char)*s++]; return w;
}
static void bmp_fill(int c,int x,int y,int w,int h) {
 (void)c;(void)y;(void)h; box_left=x;box_right=x+w;
}
static void selection_bar_backend(int c,int b,int x,int y,int w,int h) {
 (void)c;(void)b;(void)x;(void)y;(void)w;(void)h;
}
static void bmp_printf(int f,int x,int y,const char *fmt,...) {
 (void)y;assert(strcmp(fmt,"%s")==0);
 va_list ap;va_start(ap,fmt);const char *s=va_arg(ap,const char*);va_end(ap);
 char formatted[256];snprintf(formatted,sizeof(formatted),fmt,s);
 assert(strcmp(formatted,s)==0);
 int width=bmp_string_width(f,formatted);
 assert(x>=0 && x+width<=700);
 assert(box_left<=x && box_right>=x+width);
 drawn++;last_width=MAX(last_width,width);
}
'''.replace('WIDTHS', ','.join(map(str, widths)))
code += function(menu, 'pickbox_string') + '\n'
code += function(menu, 'pickbox_draw') + '\n'
groups = [
    ['Internal mic', 'L:int R:ext', 'External stereo', 'L:int R:balanced', 'Auto int/ext'],
    ['Low light', 'Exact FPS', 'Low Jello, 180d', 'HiJello, FastTv'],
    ['OFF', 'Start & CPUlens', 'Always'],
    ['OFF', 'Full', 'Half'],
    ['YUV-based, Luma', 'YUV-based, RGB', 'RAW-based (RGB)', 'RAW HistoBar (MAX)'],
    ['OFF', 'Dynamic Range', 'ETTR hint'],
    ['OFF', 'other than RAW', 'other than fine'],
    ['normal', 'Grayscale', 'Boost on WB adjust'],
    ['OFF', 'ON (fast zoom)', 'SinglePress -> 100%', 'Full zoom on AF pt.', 'Full Z on last pos.'],
    ['OFF', 'Exposure Fusion', 'Compare Images', 'Timelapse Play', 'Exposure Adjust'],
    ['Square', 'Sine', 'White Noise'],
    ['Small', 'Large', 'FullScreen'],
    ['1 EV / 8 frames', '1 EV / 16 frames', '1 EV / 32 frames',
     '1 EV / 64 frames', '1 EV / 128 frames', '1 EV / 256 frames', '1 EV / 512 frames'],
    ['OFF', 'Elapsed', 'Remain.Card', 'Remain.4GB'],
    ['Start/Stop', 'Start only', 'Stop only'],
    ['Green Bars', 'SplitScreen', 'SS ZeroCross'],
    ['50% remaining', '%s', '%n'],  # Choices are always text, never printf formats.
]
code += 'int main(void) { int checks=0;\n'
for n, choices in enumerate(groups):
    literals = ','.join(c_string(s.encode()) for s in choices)
    code += f'const char *choices{n}[]={{{literals}}};\n'
    code += f'''for(language=0;language<=1;language++)
 for(int selected=0;selected<{len(choices)};selected++)
 for(int x=250;x<=500;x+=250) {{
  struct menu_entry entry={{0,{len(choices)-1},&selected,choices{n}}};
  drawn=0;last_width=0;
  pickbox_draw(&entry,x,300);
  assert(drawn=={len(choices)});
  assert(box_left==MIN(x,700-MAX(100,last_width))-16);
  checks++;
 }}\n'''
code += 'printf("PASS: %d pickbox layout/literal-text cases, EN/RU with shipped argnor32 widths.\\n",checks);return 0;}\n'
with tempfile.TemporaryDirectory() as folder:
    p = Path(folder)
    (p/'test.c').write_text(code)
    subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                    '-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
