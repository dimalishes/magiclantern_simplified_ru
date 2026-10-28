#!/usr/bin/env python3
"""Verify Cyrillic grid alignment and render actual before/after RBF bitmaps."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from generate import ROOT, HEADER, CODES, LETTERS, encode
from cyrillic_font import bitmap, LATIN_SHAPES, make_cyrillic

before = ROOT.parent/'audit/font-before'
out = ROOT.parent/'audit'
metrics = {}
fonts = {}
for path in sorted((ROOT/'data/fonts').glob('*.rbf')):
    data=path.read_bytes();h=HEADER.unpack_from(data)
    regenerated_widths,regenerated_glyphs,_=make_cyrillic(data,h,LETTERS,path.name)
    assert bytes(regenerated_widths)==data[h[10]+160-32:h[10]+226-32]
    assert regenerated_glyphs==data[h[11]+(160-32)*h[3]:]
    box=lambda c: bitmap(data,h,ord(c) if ord(c)<128 else CODES[c]).getbbox()
    cap,small,desc=box('H'),box('x'),box('p')
    for c in LETTERS:
        b=box(c)
        assert b and 0<=b[1]<b[3]<=h[5], (path.name,c,b)
        if c in 'ДЦЩдцщфру':
            assert b[3]>cap[3], (path.name,c,b)
        else:
            assert b[3]==cap[3], (path.name,c,b,cap)
        if c not in 'ЁЙёйбф':
            assert b[1]==(cap[1] if c.isupper() else small[1]), (path.name,c,b)
    for c,latin in LATIN_SHAPES.items():
        assert bitmap(data,h,CODES[c]).tobytes()==bitmap(data,h,ord(latin)).tobytes(), (path.name,c)
        assert data[h[10]+CODES[c]-32]==data[h[10]+ord(latin)-32]
    if path.name.startswith('term'):
        assert len({data[h[10]+CODES[c]-32] for c in LETTERS})==1
        assert all(data[h[10]+CODES[c]-32]==data[h[10]+ord('H')-32] for c in LETTERS)
    metrics[path.name]={'baseline':cap[3]-1,'cap_top':cap[1],
                        'x_top':small[1],'descender_bottom':desc[3]-1,
                        'all_66_glyphs_aligned':True}
    fonts[path.name]=(data,h)

image=Image.new('RGB',(1160,1100),'#101010');draw=ImageDraw.Draw(image)
label=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',16)
draw.text((16,10),'ACTUAL RBF PIXELS / grey line = original Latin baseline / no smoothing',font=label,fill='#a0a0a0')

def put(text,x,y,font_data):
    data,h=font_data
    for code in encode(text):
        glyph=bitmap(data,h,code)
        image.paste('#ffffff',(x,y),glyph)
        x+=data[h[10]+code-h[7]]
    return x

row=45
for name in ['argnor32.rbf','argnor28.rbf','argnor23.rbf','term20.rbf','term12.rbf','arghlf22.rbf']:
    current=fonts[name];data,h=current
    previous=before/name
    draw.text((16,row),name,font=label,fill='#e5bf72');row+=24
    for title,fd in [('BEFORE',(previous.read_bytes(),HEADER.unpack_from(previous.read_bytes()))),('AFTER ',current)]:
        draw.text((16,row+2),title,font=label,fill='#9fa9b6')
        draw.line((110,row+metrics[name]['baseline']+1,1140,row+metrics[name]['baseline']+1),fill='#383838')
        put('HН AА EЕ OО PР CС TТ XХ / Настройки: Ёж, фокус, 100% LiveView',110,row,fd)
        row+=h[5]+7
    put('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',110,row,current)
    row+=h[5]+6
    put('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',110,row,current)
    row+=h[5]+16
image=image.crop((0,0,1160,row))
image.save(out/'font-grid-before-after.png')
(out/'font-grid-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print('PASS: six fonts, 66 Cyrillic glyphs each, shared Latin baseline/heights, exact lookalikes and fixed mono advances.')
print(out/'font-grid-before-after.png')
