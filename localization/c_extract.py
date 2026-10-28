"""Extract named C function definitions for host tests of the real implementation."""
import re

def function(source, name):
    # All selected functions have ordinary arguments and no braces in strings.
    m=re.search(r'(?m)^(?:static\s+)?(?:inline\s+)?(?:__attribute__\(\(noinline\)\)\s+)?(?:const\s+)?(?:char\s*\*|int|void|uint8_t\s*\*)\s*(?:FAST\s+)?'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',source)
    if not m:raise ValueError('Function not found: '+name)
    opening=source.index('{',m.start()); depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[m.start():end]
