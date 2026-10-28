#!/usr/bin/env python3
"""Check actual C display selection, RBF data preservation and render a font preview."""
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from generate import ROOT, HEADER, LETTERS, encode, catalog, c_string
from c_extract import function

entries = catalog()
archive = ROOT.parent/'magiclantern-ed3e7c0.tar.gz'
with tarfile.open(archive) as tar:
    prefix = tar.getnames()[0]
    for path in sorted((ROOT/'data/fonts').glob('*.rbf')):
        original = tar.extractfile(prefix+'/data/fonts/'+path.name).read()
        updated = path.read_bytes()
        a,b = HEADER.unpack_from(original),HEADER.unpack_from(updated)
        count = a[8]-a[7]+1
        assert b[8] == 225 and b[7] == 32
        assert updated[b[10]:b[10]+count] == original[a[10]:a[10]+count]
        assert updated[b[11]:b[11]+count*b[3]] == original[a[11]:a[11]+count*a[3]]
        assert len(updated) == b[11]+(225-32+1)*b[3]
        for code in range(160,226):
            glyph=updated[b[11]+(code-32)*b[3]:b[11]+(code-31)*b[3]]
            assert any(glyph), (path,code)
print('PASS: six fonts preserve every original glyph and width, including ML icons.')

bmp=(ROOT/'src/bmp.c').read_text()
helper=function(bmp, 'menu_ru_display')
harness='''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include "menu_ru_data.h"
typedef struct { struct { int charLast; } hdr; char *cTable; char wTable[256]; } font;
struct { void *bitmap; } font_dynamic[8];
int menu_language_ru=1;
#define FONT_ID(f) (((f)>>16)&7)
#define FONT_CANON (7u<<16)
#define FONT_LARGE (4u<<16)
'''+helper
rbf=(ROOT/'src/rbf_font.c').read_text()
for name in ('rbf_char_width','rbf_str_width','rbf_str_clipped_width','rbf_strlen_clipped'):
    match=re.search(r'(?:static inline )?int '+name+r'\([^;{}]*\)\s*\{',rbf)
    assert match, name
    opening=rbf.index('{',match.start())
    depth=1; end=opening+1
    while depth:
        depth+=(rbf[end]=='{')-(rbf[end]=='}'); end+=1
    harness+='\n'+rbf[match.start():end]+'\n'
harness=harness.replace('#include <stdio.h>','#include <stdio.h>\n#define MAX(a,b) ((a)>(b)?(a):(b))')
harness+='''\nint main(void) {
 font valid={{225},"bitmap",{0}}, old={{159},"bitmap",{0}};
 valid.wTable[160]=7; valid.wTable[225]=9;
 assert(rbf_str_width(&valid,"\\240\\341")==16);
 assert(rbf_str_width(&valid,"\\240\\n\\341")==9);
 assert(rbf_str_clipped_width(&valid,"\\240\\341",15)==7);
 assert(rbf_strlen_clipped(&valid,"\\240\\341",15)==1);
 for (int i=0;i<8;i++) font_dynamic[i].bitmap=&valid;
 const char *s="White Balance"; uint32_t f=0xA5C00000u | FONT_CANON | 0x1234;
 const char *t=menu_ru_display(s,&f);
 assert(t!=s && FONT_ID(f)==4 && (f & ~0x70000u)==((0xA5C00000u|FONT_CANON|0x1234)&~0x70000u));
 menu_language_ru=0; f=FONT_CANON; assert(menu_ru_display(s,&f)==s && f==FONT_CANON);
 menu_language_ru=1; font_dynamic[4].bitmap=&old;
 assert(menu_ru_display(s,&f)==s && f==FONT_CANON);
 font_dynamic[4].bitmap=0; assert(menu_ru_display(s,&f)==s);
 font_dynamic[4].bitmap=&valid;
 uint32_t custom_font=5u<<16;
 assert(menu_ru_display(s,&custom_font)==s && custom_font==(5u<<16));
 const char *unknown="raw_rec / %s / unknown"; assert(menu_ru_display(unknown,&f)==unknown);
 assert(menu_ru_lookup("")[0]==0);
'''
for en,ru in entries.items():
    harness+=f'assert(strcmp(menu_ru_lookup({c_string(en.encode("latin1"))}),{c_string(encode(ru))})==0);\n'
harness+='puts("PASS: all catalog lookups, language switch, missing fonts, Canon font remapping and unknown strings."); return 0; }'
with tempfile.TemporaryDirectory() as folder:
    p=Path(folder);(p/'test.c').write_text(harness)
    for char_mode in ('-fsigned-char','-funsigned-char'):
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',char_mode,'-fsanitize=undefined','-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)

# Render directly from shipped RBF bits, not a substitute desktop font.
img=Image.new('RGB',(1000,720),'#16191d')
draw=ImageDraw.Draw(img)
ui=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',16)
draw.text((24,16),'OFFLINE FONT PREVIEW - RU alpha1 / 5D2.212 (not a camera screenshot)',font=ui,fill='#b8c0cc')

def put(text,x,y,filename='argnor32.rbf',color='#ffffff'):
    data=(ROOT/'data/fonts'/filename).read_bytes();h=HEADER.unpack_from(data)
    stride=h[3]//h[5]
    for c in encode(text):
        if c==10: x=24;y+=h[5];continue
        assert h[7]<=c<=h[8]
        width=data[h[10]+c-h[7]]
        offset=h[11]+(c-h[7])*h[3]
        for yy in range(h[5]):
            for xx in range(stride*8):
                if data[offset+yy*stride+xx//8] & (1<<(xx%8)):
                    draw.point((x+xx,y+yy),fill=color)
        x+=width
    return x

put('Экспозиция',24,54,color='#f2c94c')
rows=[('Баланс белого','5500 K'),('Выдержка','1/50'),('Диафрагма','f/2.8'),('Стиль изображения','Стандартный'),('Фикс. экспозиции','ВЫКЛ'),('Язык меню','Русский')]
for i,(label,value) in enumerate(rows):
    y=101+i*40
    if i==5:draw.rectangle((16,y-4,960,y+34),fill='#284357')
    put(label,24,y);put(value,530,y,color='#c0e5ff')
put('Проверка кириллицы и служебных значков',24,365,'argnor23.rbf',color='#f2c94c')
put(LETTERS[:32],24,408,'argnor28.rbf')
put(LETTERS[32:],24,444,'argnor28.rbf')
put('Съёмка: ёж, фокус, выдержка, шрифт, щёлкнуть.',24,491,'argnor23.rbf')
put('Уровни звука: ВКЛ / ВЫКЛ',24,528,'term20.rbf')
put('Мелкий текст: АБВГД абвгд Ёё',24,562,'term12.rbf')
# Draw original icon range directly using its byte slots.
icons=(ROOT/'data/fonts/argnor28.rbf').read_bytes();h=HEADER.unpack_from(icons)
x=24;y=594
for c in range(128,160):
    stride=h[3]//h[5];offset=h[11]+(c-h[7])*h[3]
    for yy in range(h[5]):
        for xx in range(stride*8):
            if icons[offset+yy*stride+xx//8] & (1<<(xx%8)):draw.point((x+xx,y+yy),fill='#e2d5ac')
    x+=icons[h[10]+c-h[7]]+4
    if x>920:x=24;y+=35
path=ROOT.parent/'ru-font-preview.png';img.save(path)
print('Preview:',path)
