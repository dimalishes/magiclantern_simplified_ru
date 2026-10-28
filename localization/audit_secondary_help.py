#!/usr/bin/env python3
"""Check actual secondary-help selection and translation for all new help2 lines."""
import json,subprocess,tempfile
from pathlib import Path
from generate import ROOT,c_string,encode,catalog
from c_extract import function
source=(ROOT/'src/menu.c').read_text()
code=r'''#include <string.h>
#include <stdio.h>
#include <assert.h>
#include "menu_ru_data.h"
#define MENU_MAX_HELP_LEN 100
#define MIN(a,b) ((a)<(b)?(a):(b))
'''
code+=function(source,'menu_help_get_line')+'\n'+function(source,'menu_secondary_help')+'\n'
code+=r'''int main(void){
char buf[100],empty[100]="",override[100]="custom",primary[]="primary";
const char *choices="first\nsecond\nthird";
assert(!strcmp(menu_secondary_help(primary,empty,choices,1,buf),"second"));
assert(!strcmp(menu_secondary_help(primary,0,choices,2,buf),"third"));
assert(menu_secondary_help(primary,override,choices,1,buf)==override);
assert(!strcmp(menu_secondary_help(override,override,choices,1,buf),"second"));
assert(menu_secondary_help(primary,empty,0,0,buf)==0);
assert(!strcmp(menu_secondary_help(primary,empty,choices,-1,buf),"first"));
assert(!strcmp(menu_secondary_help(primary,empty,choices,99,buf),"first"));
'''
entries=catalog();metrics=json.loads((ROOT.parent/'audit/batch-200-review-metrics.json').read_text())
count=0
for m in metrics:
    if m['field']!='help2':continue
    en,ru=m['en'],m['ru'];assert entries[en]==ru
    for index,choices in [(0,en+'\nother'),(1,'other\n'+en+'\nlast'),(2,'other\nsecond\n'+en)]:
        code+=f'{{const char *selected=menu_secondary_help(primary,empty,{c_string(choices.encode())},{index},buf);\n'
        code+=f'assert(!strcmp(selected,{c_string(en.encode())}));assert(!strcmp(menu_ru_lookup(selected),{c_string(encode(ru))}));}}\n'
    count+=1
code+=f'puts("PASS: secondary help selection, overrides, bounds, {count} new help2 translations at three positions.");return 0;}}'
with tempfile.TemporaryDirectory() as folder:
    p=Path(folder);(p/'test.c').write_text(code)
    subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-I'+str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
