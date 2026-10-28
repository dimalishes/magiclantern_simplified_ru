"""Compile the approved finite display templates; no input format is interpreted."""
import json,re,itertools
from generate import ROOT,encode,c_string
TOKEN=re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[dsxX]|%)')
def parts(s):
    literals=[''];specs=[];end=0
    for m in TOKEN.finditer(s):
        gap=s[end:m.start()];assert '%' not in gap, s
        literals[-1]+=gap;end=m.end()
        if m[0]=='%%':literals[-1]+='%'
        else:specs.append(m[0]);literals.append('')
    tail=s[end:];assert '%' not in tail, s
    literals[-1]+=tail
    return literals,specs

def generate_patterns(entries):
    rows=json.loads((ROOT/'localization/final-ru.json').read_text())
    records=[]
    for m in rows:
        assert entries[m['en']]==m['ru']
        if m['kind']=='template' or m['kind']=='icon' and TOKEN.search(m['en']):
            a,sa=parts(m['en']);b,sb=parts(m['ru']);assert sa==sb,(m,sa,sb)
            assert sa and len(sa)<=12
            records.append((int(m['id']) if isinstance(m['id'],int) else 2000+int(m['id'].split('-')[1]),m['en'],m['ru']))
    aux=[
      (3001,'%s of %s','%s из %s'),
      (3002,'%s, %s used','%s, занято %s'),
      (3003,'%s%d %s','%s%d %s'),
      (3004,'%s: %d...','%s: %d...'),
      (3005,'Trap Focus: %s','Trap Focus: %s'),
      (3006,'Green %d','Зелёный %d'),(3007,'Magenta %d','Пурпурный %d'),
      (3008,'Amber %d','Янтарный %d'),(3009,'Blue %d','Синий %d'),
      (3010,'%ds','%d с'),(3011,'%dmin','%d мин'),
      (3012,'after %ds','через %d с'),(3013,'after %dmin','через %d мин'),
      (3014,'ON, %s','ВКЛ, %s'),
      (3015,'FW default(reboot)','Штатный(перезапуск)'),
      (3016,'QScale %s%d','QScale %s%d'),
      (3020,'[FAIL] %s','[ОШИБКА] %s'),
      (3021,'%s, peak %s','%s, пик %s'),
      (3022,'%s:%d task %s','%s:%d задача %s'),
      (3023,'%dh%dm%ds','%d ч %d мин %d с'),
      (3024,'%dm%ds','%d мин %d с'),
      (3025,'%dh%dm','%d ч %d мин'),
      (3026,'%dh%ds','%d ч %d с'),
      (3027,'%d ms','%d мс'),
      (3028,'%d \x84s','%d мкс'),
      (3030,'%dm','%d мин'),
    ]
    # Finite concatenations produced by the memory diagnostics' append calls.
    base='%d tracked small blocks (%s), %d total (%s), '
    rubase='Малых блоков: %d (%s), всего %d (%s), '
    for n,mask in enumerate(itertools.product((False,True),repeat=3)):
        en=base+'\noverhead %s (dynamic)';ru=rubase+'\nрасходы: %s (динамические)'
        for use,a,b in zip(mask,[' + %s (fixed)',' + %s (history)',', peak %s'],[' + %s (постоянные)',' + %s (история)',', пик %s']):
            if use:en+=a;ru+=b
        aux.append((3100+n,en,ru))
    existing={en for _,en,_ in records}
    records += [m for m in aux if m[1] not in existing or m[0] == 3030]
    # Specific literal structure wins over a more general string argument.
    records.sort(key=lambda m:sum(len(x) for x in parts(m[1])[0]),reverse=True)
    out=['/* Generated finite approved display patterns. */',
      '#define MENU_RU_MAX_ARGS 12',
      'struct menu_ru_pattern { unsigned short id; unsigned char count; const char *types; const char *en[MENU_RU_MAX_ARGS+1]; const char *ru[MENU_RU_MAX_ARGS+1]; };',
      'static const struct menu_ru_pattern menu_ru_patterns[] = {']
    for id,en,ru in records:
        a,sa=parts(en);b,sb=parts(ru);assert sa==sb
        typ=''.join('s' if x.endswith('s') else 'x' if x[-1] in 'xX' else 'd' for x in sa)
        # Padding widths are preserved as bytes from the already formatted input.
        out.append('{%d,%d,%s,{%s},{%s}},'%(id,len(sa),c_string(typ.encode()),
            ','.join(c_string(x.encode('latin1')) for x in a),','.join(c_string(encode(x)) for x in b)))
    out+=['};']
    buckets={}
    for index,(_,en,_) in enumerate(records):
        prefix=parts(en)[0][0]; first=ord(prefix[0]) if prefix else 0
        buckets.setdefault(first,[]).append(index)
    order=[]; offsets={}
    for first,indices in sorted(buckets.items()):
        offsets[first]=(len(order),len(indices));order.extend(indices)
    out+=['static const unsigned short menu_ru_order[] = {'+','.join(map(str,order))+'};',
           'static const struct {unsigned short offset,count;} menu_ru_buckets[256] = {']
    out += ['[%d]={%d,%d},'%(first,*value) for first,value in offsets.items()]
    out += ['};']
    # Exact argument aliases are legal only in their explicitly assigned role.
    aliases={
      1:[('connected','есть'),('disconnected','нет')],
      2:[('(reboot)','(перезапуск)')],
      3:[('Focus stack','Focus Stacking'),('steps from here','шагов от текущей точки'),('(here)','(здесь)'),('LCD sensor','Датчик LCD')],
      4:[('0.001% px','0.001% пикс.'),('0.01% px','0.01% пикс.'),('0.1% px','0.1% пикс.'),('1% px','1% пикс.'),('Gradual','Плавно')],
      5:[('Module disabled','Модуль выключен'),('Module not loaded','Модуль не загружен'),('Seems linking failed. Unknown symbols?','Ошибка связывания. Неизвестные символы?'),('Linking failed','Ошибка связывания'),('Module init failed','Сбой инициализации модуля'),('Module loaded successfully','Модуль успешно загружен')],
      6:[('ON','ВКЛ'),('OFF','ВЫКЛ')],
      7:[('HDR bracketing','HDR-брекетингом'),('trap focus','Trap Focus'),('bulb shots','выдержкой Bulb'),('intervalometer','интервалометром'),('motion detection','детектором движения'),('Canon bracketing (AEB)','брекетингом Canon (AEB)'),('audio remote','спуском по звуку')],
      8:[('half-shutter','полунажатия спуска'),('first picture','первого снимка')],
      9:[('0 (Grayscale)','0 (чёрно-белый)'),('Low','Низкая'),('Normal','Обычная'),('High','Высокая'),('Very high','Очень высокая')],
      10:[('in LiveView and ','в LiveView и ')],
      14:[('sec',' с'),('min',' мин')],
      15:[(' Infty',entries[' Infty'])],
      13:[('ID error','ошибка ID'),('double free','повторное освобождение'),('unknown error','неизвестная ошибка'),('underflow','underflow'),('overflow','overflow')],
    }
    out+=['struct menu_ru_alias { unsigned char role; const char *en; const char *ru; };','static const struct menu_ru_alias menu_ru_aliases[] = {']
    for role,pairs in aliases.items():
        for en,ru in pairs:out.append('{%d,%s,%s},'%(role,c_string(en.encode()),c_string(encode(ru))))
    out+=['};','static const struct { const char *en; const char *ru; } menu_ru_settings[] = {']
    for m in rows:
        if isinstance(m['id'],int) and 1676<=m['id']<=1685:
            assert m['en'].endswith('%s') and m['ru'].endswith('%s')
            out.append('{%s,%s},'%(c_string(m['en'][:-2].encode()),c_string(encode(m['ru'][:-2]))))
    out+=['};']
    (ROOT/'src/menu_ru_patterns.h').write_text('\n'.join(out)+'\n')
    (ROOT/'localization/final-runtime-patterns.json').write_text(json.dumps([{'id':id,'en':en,'ru':ru} for id,en,ru in records],ensure_ascii=False,indent=2)+'\n')
    print('Generated',len(records),'bounded display patterns.')
