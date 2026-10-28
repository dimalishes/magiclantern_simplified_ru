#!/usr/bin/env python3
"""Pixel-compare real BMP/RBF output for all formatted runtime fixtures."""
from pathlib import Path
import subprocess
from generate import ROOT
from c_extract import function
out=ROOT.parent/'audit'
renderer=(out/'renderer-test.c').read_text()
code=renderer[:renderer.index('int main(int argc,char **argv)')]
runtime=(out/'final-runtime-test.c').read_text()
code+=runtime[runtime.index('struct test {int id;'):runtime.index('int main(void)')]
bmp=(ROOT/'src/bmp.c').read_text()
code=code.replace(function(code,'bmp_translate_dynamic'),function(bmp,'bmp_translate_dynamic'))
code+=function(bmp,'bmp_literal_width')+'\n'+function(bmp,'bmp_draw_literal')+'\n'
code+=r'''
static uint8_t expected_frame[sizeof(framebuffer)];
int main(int argc,char **argv){assert(argc==7);unsigned checks=0;
for(int fi=1;fi<argc;fi++){
 font f=load_font(argv[fi]);for(int i=0;i<8;i++)font_dynamic[i].bitmap=&f;
 for(unsigned t=0;t<sizeof(tests)/sizeof(tests[0]);t++){
  const struct test v=tests[t];char original[128],translated[128];strcpy(original,v.en);strcpy(translated,v.ru);
  uint32_t spec=FONT(FONT_LARGE,1,0)|SHADOW_MASK;
  int width=bmp_string_width(spec,original),expected=rbf_str_width(&f,translated);
  if(width!=expected){fprintf(stderr,"Width mismatch id %d: %s\n",v.id,v.en);return 1;}
  memset(framebuffer,0,sizeof(framebuffer));
  int direct=rbf_draw_string(&f,10,20,translated,spec);memcpy(expected_frame,framebuffer,sizeof(framebuffer));
  memset(framebuffer,0,sizeof(framebuffer));int x=10,y=20;
  int actual=bmp_puts(spec,&x,&y,original);
  assert(actual==direct && !strcmp(original,v.en));
  if(memcmp(framebuffer,expected_frame,sizeof(framebuffer))){fprintf(stderr,"Pixel mismatch id %d: %s\n",v.id,v.en);return 1;}
  menu_language_ru=0;assert(bmp_string_width(spec,original)==rbf_str_width(&f,original));menu_language_ru=1;
  checks++;
 }
 /* Literal numeric editing uses original glyphs even with Russian enabled. */
 char raw[]="20s",copy[128];strcpy(copy,raw);uint32_t spec=FONT(FONT_LARGE,1,0);
 assert(bmp_literal_width(spec,raw)==rbf_str_width(&f,raw));
 memset(framebuffer,0,sizeof(framebuffer));int expected=rbf_draw_string(&f,10,20,copy,spec);
 memcpy(expected_frame,framebuffer,sizeof(framebuffer));memset(framebuffer,0,sizeof(framebuffer));
 assert(bmp_draw_literal(spec,10,20,raw)==expected);
 assert(!memcmp(expected_frame,framebuffer,sizeof(framebuffer)) && !strcmp(raw,"20s"));
 free(f.cTable);
}
printf("PASS: %u pixel-identical formatted message cases across six shipped RBF fonts.\n",checks);return 0;}
'''
(out/'final-render-test.c').write_text(code)
fonts=[str(p) for p in sorted((ROOT/'data/fonts').glob('*.rbf'))]
for mode in ['signed','unsigned']:
 exe=out/('final-render-test-'+mode)
 subprocess.run(['gcc','-std=c99','-O1','-g','-f'+mode+'-char','-fsanitize=address,undefined','-fno-sanitize-recover=all',
  '-I'+str(ROOT/'src'),str(out/'final-render-test.c'),'-o',str(exe)],check=True)
 subprocess.run([str(exe),*fonts],check=True)
