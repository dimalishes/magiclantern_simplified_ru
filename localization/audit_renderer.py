#!/usr/bin/env python3
"""Run actual RBF rendering / display integration under ASan and UBSan.
Hardware pixel output and Canon ROM fonts are stubbed; RBF algorithms are real.
"""
from pathlib import Path
import subprocess
from generate import ROOT
from c_extract import function

out=ROOT.parent/'audit';out.mkdir(exist_ok=True)
rbf=(ROOT/'src/rbf_font.c').read_text(); bmp=(ROOT/'src/bmp.c').read_text(); hdr=(ROOT/'src/bmp.h').read_text()
defs=hdr[hdr.index('#define FONT_MASK'):hdr.index('/* RBF stuff */')]
code='''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "rbf_font.h"
#include "menu_ru_data.h"
#define FAST
#define CONFIG_MENU_RU
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define ABS(a) ((a)<0?-(a):(a))
#define SGN(a) (((a)>0)-((a)<0))
#define COERCE(x,a,b) MAX((a),MIN((b),(x)))
#define BMP_W_MINUS -120
#define BMP_W_PLUS 840
#define BMP_H_MINUS -30
#define BMP_H_PLUS 510
#define COLOR_WHITE 1
#define COLOR_BLACK 0
#define NO_BG_ERASE 3
#define FONT_CONDENSED 0x00100000
#define FG_COLOR(f) FONT_FG(f)
#define BG_COLOR(f) FONT_BG(f)
'''+defs+'''
struct { void *bitmap; } font_dynamic[8];
int menu_language_ru=1;
uint32_t ml_refresh_display_needed;
static uint8_t framebuffer[960*540];
static uint8_t *bmp_vram(void) {return framebuffer;}
static unsigned long pixels;
static void bmp_putpixel_fast(uint8_t *p,int x,int y,uint8_t color) {
 if(x>=BMP_W_MINUS && x<BMP_W_PLUS && y>=BMP_H_MINUS && y<BMP_H_PLUS)
 {p[(y-BMP_H_MINUS)*960+x-BMP_W_MINUS]=color;pixels++;}
}
static void bmp_fill(uint8_t color,int x,int y,int w,int h) {
 x=COERCE(x,BMP_W_MINUS,BMP_W_PLUS-1);y=COERCE(y,BMP_H_MINUS,BMP_H_PLUS-1);
 w=COERCE(w,0,BMP_W_PLUS-x-1);h=COERCE(h,0,BMP_H_PLUS-y-1);
 for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++)bmp_putpixel_fast(framebuffer,x+xx,y+yy,color);
}
static void bfnt_draw_char(int ch,int x,int y,int fg,int bg) {(void)ch;(void)x;(void)y;(void)fg;(void)bg;}
static uint32_t fontspec_fg(uint32_t f){return FONT_FG(f);}
static uint32_t fontspec_bg(uint32_t f){return FONT_BG(f);}
'''
for name in ('rbf_font_char','rbf_char_width','rbf_str_width','rbf_str_clipped_width','rbf_strlen_clipped','font_draw_char','font_draw_char_shadow','rbf_draw_char','rbf_draw_string_c','rbf_draw_string_simple','rbf_draw_clipped_string','rbf_draw_string_single_line','rbf_draw_string'):
    code+=function(rbf,name)+'\n'
for name in ('menu_ru_display','bmp_translate_string'):
    code+=function(bmp,name)+'\n'
code+='#include "menu_ru_runtime.h"\n'
for name in ('bmp_translate_dynamic','bmp_translate_module_summary','bmp_translate_module_name','menu_ru_draw','menu_ru_dynamic_draw','menu_ru_dynamic_width','bmp_puts','bmp_string_width'):
    code+=function(bmp,name)+'\n'
code+='''
static font load_font(const char *path) {
 font f={0};FILE *fp=fopen(path,"rb");assert(fp);
 assert(fread(&f.hdr,1,sizeof(f.hdr),fp)==sizeof(f.hdr));
 assert(f.hdr.charFirst==32 && f.hdr.charLast==225 && f.hdr.height>0);
 f.charCount=f.hdr.charLast-f.hdr.charFirst+1;f.width=8*f.hdr.charSize/f.hdr.height;
 assert(f.hdr.charSize%f.hdr.height==0);
 fseek(fp,f.hdr._wmapAddr,SEEK_SET);assert(fread(f.wTable+32,1,f.charCount,fp)==(size_t)f.charCount);
 f.cTableSize=f.charCount*f.hdr.charSize;f.cTable=malloc(f.cTableSize);assert(f.cTable);
 fseek(fp,f.hdr._cmapAddr,SEEK_SET);assert(fread(f.cTable,1,f.cTableSize,fp)==(size_t)f.cTableSize);fclose(fp);
 for(int c=32;c<=225;c++)assert((unsigned char)f.wTable[c]<=f.width);
 return f;
}
int main(int argc,char **argv) {
 assert(argc==7); unsigned tests=0;
 for(int fi=1;fi<argc;fi++) {
  font f=load_font(argv[fi]);for(int id=0;id<8;id++)font_dynamic[id].bitmap=&f;
  unsigned common_count=sizeof(menu_ru_catalog)/sizeof(menu_ru_catalog[0]);
  unsigned summary_count=sizeof(module_ru_summaries)/sizeof(module_ru_summaries[0]);
  unsigned name_count=sizeof(module_ru_names)/sizeof(module_ru_names[0]);
  for(unsigned i=0;i<common_count+summary_count+name_count;i++) {
   const char *original, *translated;
   if(i<common_count) {
    original=menu_ru_catalog[i].en; translated=menu_ru_catalog[i].ru;
   } else if(i<common_count+summary_count) {
    unsigned j=i-common_count;
    original=bmp_translate_module_summary(FONT_LARGE,module_ru_summaries[j].en);
    translated=module_ru_summaries[j].ru;
    assert(!strcmp(original,translated));
   } else {
    unsigned j=i-common_count-summary_count;
    original=bmp_translate_module_name(FONT_LARGE,module_ru_names[j].en);
    translated=module_ru_names[j].ru;
    assert(!strcmp(original,translated));
   }
   assert(strlen(translated)<128);
   for(unsigned a=0;a<4;a++)for(unsigned shadow=0;shadow<2;shadow++)for(unsigned narrow=0;narrow<3;narrow++) {
    unsigned fs=FONT(FONT_LARGE,1,0)|(a<<24)|(shadow?SHADOW_MASK:0)|(narrow?FONT_TEXT_WIDTH(narrow==1?96u:640u):0);
    int x=a==1?360:a==2?700:10, y=20;
    int expected=rbf_str_width(&f,translated);
    assert(bmp_string_width(fs,original)==expected);
    char scratch[128],before[128];strcpy(scratch,translated);strcpy(before,scratch);
    int direct=rbf_draw_string(&f,x,y,scratch,fs);assert(strcmp(scratch,before)==0);
    char formatted[128]; strcpy(formatted,original);
    int displayed=bmp_puts(fs,&x,&y,formatted);assert(displayed==direct);tests++;
   }
   menu_language_ru=0;
   assert(bmp_string_width(FONT_LARGE,original)==rbf_str_width(&f,original));
   menu_language_ru=1;
  }
  // Border coordinates, long strings, multiline alignment, every glyph.
  for(int a=0;a<4;a++)for(int y=-30;y<=510;y+=54) {
   char text[512],before[512];int p=0;
   for(int repeat=0;repeat<2;repeat++)for(int c=32;c<=225;c++)text[p++]=(char)c;
   text[64]='\\n';text[222]='\\n';text[p]=0;memcpy(before,text,p+1);
   rbf_draw_string(&f,-120,y,text,FONT(FONT_LARGE,1,0)|(a<<24)|SHADOW_MASK|FONT_TEXT_WIDTH(640u));
   assert(memcmp(before,text,p+1)==0);tests++;
  }
  free(f.cTable);
 }
 printf("PASS: %u actual rendering/integration cases; %lu framebuffer writes; ASan+UBSan.\\n",tests,pixels);
 return 0;
}
'''
(out/'renderer-test.c').write_text(code)
fonts=[str(p) for p in sorted((ROOT/'data/fonts').glob('*.rbf'))]
for mode in ('signed','unsigned'):
    exe=out/('renderer-test-'+mode)
    subprocess.run(['gcc','-std=c99','-O1','-g','-f'+mode+'-char','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-I'+str(ROOT/'src'),str(out/'renderer-test.c'),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe),*fonts],capture_output=True,text=True)
    (out/('renderer-'+mode+'.log')).write_text(result.stdout+result.stderr)
    print(result.stdout,end='');print(result.stderr,end='');result.check_returncode()
