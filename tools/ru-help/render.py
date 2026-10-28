#!/usr/bin/env python3
"""Render reviewed EN/RU RST guide into EOS indexed RLE8 help pages."""
from pathlib import Path
import re,json,struct,hashlib,io
from PIL import Image,ImageDraw,ImageFont,ImageStat
from docutils.core import publish_doctree
from docutils import nodes
R=Path(__file__).resolve().parents[2]
SRC=R
DOC=SRC/'doc';OUT=DOC/'cam';AUDIT=Path(__file__).resolve().parent;PREVIEW=AUDIT/'preview'
FILES=['MANUAL.txt','MN-AUDIO.txt','MN-EXPO.txt','MN-OVERLAY.txt','MN-MOVIE.txt','MN-SHOOT.txt','MN-FOCUS.txt','MN-DISPLAY.txt','MN-PREFS.txt','MN-DEBUG.txt','EPILOGUE.txt']
FONTS=next((p for p in [Path('/usr/share/fonts/TTF'), Path('/usr/share/fonts/truetype/dejavu')] if (p/'DejaVuSans.ttf').is_file()), Path('/usr/share/fonts/TTF'))
BODY=ImageFont.truetype(str(FONTS/'DejaVuSans.ttf'),22)
BOLD=ImageFont.truetype(str(FONTS/'DejaVuSans-Bold.ttf'),22)
TITLE=ImageFont.truetype(str(FONTS/'DejaVuSans-Bold.ttf'),26)
SMALL=ImageFont.truetype(str(FONTS/'DejaVuSans.ttf'),18)
# The EOS ignores BMP RGB palette entries; pixels must use native palette indices.
palette=Image.open(SRC/'data/vram/Palette.jpg').convert('RGB');cw,ch=palette.width/16,palette.height/16
colors=[]
for i in range(256):
 x,y=(i%16)*cw,(i//16)*ch
 colors.append(tuple(round(v) for v in ImageStat.Stat(palette.crop((x+5,y+5,x+cw-5,y+ch-5))).mean))
colors[1]=(255,255,255);colors[2]=(0,0,0)
flat=[v for c in colors for v in c]
safe=[i for i in range(1,80) if i not in (3,20)]
quant_palette=Image.new('P',(1,1));quant_palette.putpalette([v for i in (safe+[2]*(256-len(safe))) for v in colors[i]])
map_palette=bytes(safe+[2]*(256-len(safe)))
def native_image(path):
 im=Image.open(path).convert('RGB');im.thumbnail((650,210),Image.Resampling.LANCZOS)
 q=im.quantize(palette=quant_palette,dither=Image.Dither.NONE)
 q=Image.frombytes('P',q.size,q.tobytes().translate(map_palette));q.putpalette(flat)
 return q
# Regenerate the missing montage referenced by the original guide, from its existing assets.
if not (DOC/'Cropmarks550D.png').exists():
 montage=Image.new('RGB',(720,150),'black');d=ImageDraw.Draw(montage)
 for n,name in enumerate(['CineSco2','CrssMtr2','Passport','PhiPhoto']):
  im=Image.open(SRC/f'data/cropmks/{name}.bmp').convert('RGB');im.thumbnail((174,120))
  montage.paste(im,(n*180+(180-im.width)//2,0));d.text((n*180+4,126),name,font=SMALL,fill='white')
 montage.save(DOC/'Cropmarks550D.png')
def normalize(text):
 text=re.sub(r'`([^`<>]+) <[^>]+>`__?',r'\1',text)
 text=re.sub(r'`([^`]+)`_',r'\1',text)
 return text.replace('\u00a0',' ').replace('⨂','').replace('⨀','').replace('〰','').strip()
def preprocess(text,lang):
 text='\n'.join(l for l in text.splitlines() if not l.startswith('#'))
 # Old wiki media macros are not RST. Make their visible meaning explicit.
 def video(m):
  title=m[2].strip() if m[2] else ''
  return ('Видео' if lang=='ru' else 'Video')+(': '+title if title else '')+' (Vimeo '+m[1]+'). '
 text=re.sub(r'\{\{\s*vimeo>(\d+)[^}|]*(?:\|([^}]*))?\}\}',video,text)
 def photo(m):
  name=m[1].lstrip(':').strip();path=DOC/name
  if path.is_file():return '\n\n.. figure:: '+str(path)+'\n\n'
  return '' # optional historical online media has no locally available picture
 text=re.sub(r'\[\[https?://[^|\]]+\|\s*(\{\{[^}]+\}\})\s*\]\]',lambda m:m[1],text)
 text=re.sub(r'\{\{\s*([^>?|}\s]+)[^}]*\}\}',photo,text)
 text=re.sub(r'\[\[([^\]]+)\]\]',lambda m:m[1],text)
 return text

def units(text,lang):
 tree=publish_doctree(preprocess(text,lang),settings_overrides={'warning_stream':io.StringIO(),'report_level':5,'halt_level':6,'file_insertion_enabled':False})
 result=[]
 def visit(node):
  if isinstance(node,(nodes.document,nodes.section)):
   title=next((x for x in node.children if isinstance(x,nodes.title)),None)
   if title is not None:
    result.append((normalize(title.astext()),list(node.get('names',[])),[x for x in node.children if not isinstance(x,(nodes.title,nodes.section))]))
   for child in node.children:
    if isinstance(child,nodes.section):visit(child)
 visit(tree)
 return result

def blocks(ns,lang,base,depth=0):
 out=[]
 for node in ns:
  if isinstance(node,(nodes.target,nodes.system_message,nodes.comment,nodes.raw)):continue
  if isinstance(node,nodes.paragraph):
   text=normalize(node.astext())
   if text:out.append(('text',text,depth,''))
  elif isinstance(node,(nodes.bullet_list,nodes.enumerated_list)):
   for i,item in enumerate(node.children):
    children=blocks(item.children,lang,base,depth+1)
    marker=(str(node.get('start',1)+i)+'. ') if isinstance(node,nodes.enumerated_list) else '• '
    if children:
     kind,value,indent,prefix=children[0]
     if kind=='text':children[0]=(kind,value,indent,marker)
    out.extend(children)
  elif isinstance(node,nodes.image):
   path=Path(node['uri']);path=path if path.is_absolute() else base/path
   if path.is_file():out.append(('image',str(path),depth,''))
   else:raise FileNotFoundError(path)
  elif isinstance(node,nodes.note):
   children=blocks(node.children,lang,base,depth)
   if children and children[0][0]=='text':
    k,v,d,p=children[0];children[0]=(k,('Примечание: ' if lang=='ru' else 'Note: ')+v,d,p)
   out.extend(children)
  elif isinstance(node,nodes.title):continue
  elif node.children:out.extend(blocks(node.children,lang,base,depth))
 return out

def wrap(text,font,width):
 lines=[];line=''
 for word in text.split():
  trial=(line+' '+word).strip()
  if font.getlength(trial)<=width:line=trial;continue
  if line:lines.append(line);line=''
  # Preserve long paths/technical tokens without overflowing.
  while font.getlength(word)>width:
   n=1
   while n<len(word) and font.getlength(word[:n+1])<=width:n+=1
   lines.append(word[:n]);word=word[n:]
  line=word
 if line:lines.append(line)
 return lines or ['']

def rle8(im):
 assert im.mode=='P' and im.size==(720,480)
 raw=im.tobytes();data=bytearray()
 for y in range(479,-1,-1):
  row=raw[y*720:(y+1)*720];x=0
  while x<720:
   end=x+1
   while end<720 and end-x<255 and row[end]==row[x]:end+=1
   data.extend((end-x,row[x]));x=end
  data.extend((0,0))
 data.extend((0,1));offset=54+1024
 return b'BM'+struct.pack('<IHHI',offset+len(data),0,0,offset)+struct.pack('<IiiHHIIiiII',40,720,480,1,8,1,len(data),2835,2835,256,256)+bytes(v for c in colors for v in (c[2],c[1],c[0],0))+data

class Pages:
 def __init__(self,lang):self.lang=lang;self.pages=[];self.keymap={};self.unitmeta=[];self.current=None
 def text(self,draw,x,y,text,font,color=1):
  assert 18<=x<703 and x+font.getlength(text)<=703,(self.lang,text)
  assert 0<=y and y+font.getbbox(text)[3]-font.getbbox(text)[1]<479,(y,text)
  draw.text((x,y),text,font=font,fill=color,anchor='lt')
 def new(self,chapter,title):
  im=Image.new('P',(720,480),2);im.putpalette(flat);d=ImageDraw.Draw(im)
  self.text(d,20,12,'Magic Lantern  •  '+self.lang.upper()+'  •  '+chapter,SMALL)
  d.line((20,38,700,38),fill=1)
  y=48
  for line in wrap(title,TITLE,680):self.text(d,20,y,line,TITLE);y+=32
  self.current={'image':im,'chapter':chapter,'title':title,'y':y+10,'lines':[],'images':[]};self.pages.append(self.current)
 def add(self,chapter,title,content,keys):
  start=len(self.pages)+1;self.new(chapter,title)
  for kind,value,depth,marker in content:
   if kind=='image':
    im=native_image(value)
    if self.current['y']+im.height>432:self.new(chapter,title)
    self.current['image'].paste(im,((720-im.width)//2,self.current['y']));self.current['images'].append(Path(value).name);self.current['y']+=im.height+10
   else:
    x=20+min(depth,3)*16;prefix=marker
    lines=wrap(prefix+value,BODY,700-x)
    for line in lines:
     if self.current['y']+26>432:self.new(chapter,title)
     d=ImageDraw.Draw(self.current['image']);self.text(d,x,self.current['y'],line,BODY);self.current['lines'].append(line);self.current['y']+=28
    self.current['y']+=9
  for key in keys:
   k=' '.join(key.lower().split())
   if k and k not in self.keymap:self.keymap[k]=start
  self.unitmeta.append({'chapter':chapter,'title':title,'first_page':start,'last_page':len(self.pages),'blocks':len(content)})
  return start
 def save(self):
  dest=OUT/self.lang;dest.mkdir(parents=True,exist_ok=True);(PREVIEW/self.lang).mkdir(parents=True,exist_ok=True)
  assert len(self.pages)<1000
  for folder,extension in [(dest,'.bmh'),(PREVIEW/self.lang,'.png')]:
   for old in folder.glob('page-*'+extension):
    if int(old.stem.split('-')[1])>len(self.pages):old.unlink()
  for number,p in enumerate(self.pages,1):
   d=ImageDraw.Draw(p['image']);d.line((20,442,700,442),fill=1)
   footer=('Стрелки/диск: листать • INFO/SET: назад' if self.lang=='ru' else 'Arrows/dial: pages • INFO/SET: back')
   self.text(d,20,452,footer,SMALL);count=f'{number}/{len(self.pages)}';self.text(d,700-SMALL.getlength(count),452,count,SMALL)
   data=rle8(p['image']);(dest/f'page-{number:03d}.bmh').write_bytes(data)
   p['image'].convert('RGB').save(PREVIEW/self.lang/f'page-{number:03d}.png')
  self.keymap['end']=len(self.pages)
  (dest/'menuidx.dat').write_text(''.join(f'{number:03d} {key}\n' for key,number in sorted(self.keymap.items())),encoding='ascii')

models={};baseunits={}
for lang in ['en','ru']:
 book=Pages(lang);book.add('Magic Lantern','Справка Magic Lantern' if lang=='ru' else 'Magic Lantern guide',[('text','Русский перевод исходного руководства. Ограничения по моделям сохранены.' if lang=='ru' else 'Original guide. Availability and limitations depend on the camera model.',0,'')],['About Magic Lantern'])
 book.add('Magic Lantern','Оглавление' if lang=='ru' else 'Contents',[],['Complete user guide','Contents'])
 allunits=[];chapters=[]
 for filename in FILES:
  e=units((DOC/filename).read_text(),'en');u=units((DOC/('ru/'+filename if lang=='ru' else filename)).read_text(),lang)
  assert len(e)==len(u),(filename,len(e),len(u))
  base=DOC/'ru' if lang=='ru' else DOC
  chapter=u[0][0];chapter_page=len(book.pages)+1;chapters.append((filename,chapter,chapter_page))
  for (et,enkeys,_),(ut,ukeys,body) in zip(e,u):
   keys=[et,*enkeys]
   # Explicit aliases from old source and current menu keys are kept ASCII.
   keys=[k for k in keys if k.isascii()]
   content=blocks(body,lang,base)
   if lang=='en' and et=='Intervalometer':
    content.insert(1,('text','Note: stopping a no-delay sequence (0 s interval) has been fixed. Press PLAY to stop. If the start trigger is Leave Menu, switch the intervalometer OFF before leaving the ML menu to prevent a new sequence.',0,''))
   book.add(chapter,ut,content,keys)
 allunits=book.unitmeta
 # Bind renamed modern menu entries to the relevant historical section.
 aliases=json.loads((AUDIT/'menu-aliases.json').read_text())
 for key,target in aliases.items():
  target=target.lower()
  assert target in book.keymap,(lang,key,target)
  book.keymap[key.lower()]=book.keymap[target]
 # The contents page is populated after every chapter start page is known.
 page=book.pages[1];d=ImageDraw.Draw(page['image']);y=page['y']
 for filename,title,number in chapters:
  text=f'{number:03d}  {title}'
  book.text(d,20,y,text,BODY);page['lines'].append(text);y+=28
 assert y<436
 book.save();models[lang]={'pages':len(book.pages),'index_keys':len(book.keymap),'chapters':[{'file':f,'title':t,'page':p} for f,t,p in chapters],'units':allunits,'page_content':[{'number':i,'chapter':p['chapter'],'title':p['title'],'text_lines':p['lines'],'images':p['images']} for i,p in enumerate(book.pages,1)]}
# Complete-guide entries use unchanged internal names and privileges.
entries=['/* Generated by audit/help-pages/render.py. English lookup keys are stable. */','{ .name = "Help", .priv = "Contents", .select = menu_help_go_to_label, .update = user_guide_display, .icon_type = IT_ACTION },','{ .name = "Key Shortcuts", .priv = "Key shortcuts", .select = menu_help_go_to_label, .update = user_guide_display, .icon_type = IT_ACTION },']
for name in ['Audio','Expo','Overlay','Movie','Shoot','Focus','Display','Prefs','Debug']:
 entries.append('{ .name = "%s", .priv = "%s", .select = menu_help_go_to_label, .update = user_guide_display, .icon_type = IT_ACTION },'%(name,name))
(SRC/'src/menuindexentries.h').write_text('\n'.join(entries)+'\n')
(AUDIT/'pages.json').write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'pages':v['pages'],'index_keys':v['index_keys']} for k,v in models.items()}))
