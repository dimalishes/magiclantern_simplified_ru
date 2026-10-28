/* Display-only matching against generated, approved literal patterns.
 * Input is already formatted. Captured bytes are copied, never printf formats.
 * No allocation, shared scratch storage, input writes or unbounded recursion.
 */
#include "menu_ru_patterns.h"
#define MENU_RU_DISPLAY_LIMIT 127
struct menu_ru_capture { unsigned char start, length; };

static int menu_ru_append(char *out, size_t capacity, size_t *used,
                          const char *text, size_t length)
{
    if (*used >= capacity || length >= capacity - *used) return 0;
    memcpy(out + *used, text, length); *used += length; out[*used] = 0;
    return 1;
}

static int menu_ru_capture_valid(char type, const char *text, unsigned length)
{
    if (type == 's') return 1;
    unsigned i = 0, digits = 0;
    while (i < length && text[i] == ' ') i++;
    if (type == 'd' && i < length && (text[i] == '-' || text[i] == '+')) i++;
    for (; i < length; i++)
    {
        char c = text[i];
        if (c >= '0' && c <= '9') digits++;
        else if (type == 'x' && ((c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) digits++;
        else return 0;
    }
    return digits && digits <= (type == 'x' ? 16u : 10u);
}

static int menu_ru_match(const struct menu_ru_pattern *pattern,
                          const char *text, unsigned length,
                          struct menu_ru_capture captures[MENU_RU_MAX_ARGS])
{
    unsigned char positions[MENU_RU_MAX_ARGS+1], next[MENU_RU_MAX_ARGS+1];
    size_t prefix = strlen(pattern->en[0]);
    if (prefix > length || memcmp(text, pattern->en[0], prefix)) return 0;
    size_t suffix = strlen(pattern->en[pattern->count]);
    if (suffix > length || memcmp(text + length - suffix, pattern->en[pattern->count], suffix)) return 0;
    int depth = 0; positions[0] = prefix; next[0] = 0;
    /* Finite work cap even for adversarial strings with repeated separators. */
    unsigned budget = 4096;
    while (depth >= 0 && budget--)
    {
        if (depth == pattern->count)
        {
            if (positions[depth] == length) return 1;
            depth--; continue;
        }
        unsigned start = positions[depth], attempt = next[depth]++;
        if (attempt > length - start)
        {
            depth--; continue;
        }
        /* A numeric field followed directly by a unit string consumes its
         * complete digit run, rather than leaving digits inside the unit. */
        unsigned n = pattern->types[depth] == 's' ? attempt : length - start - attempt;
        if (!menu_ru_capture_valid(pattern->types[depth], text + start, n)) continue;
        const char *literal = pattern->en[depth+1]; size_t size = strlen(literal);
        if (n + size > length - start || memcmp(text + start + n, literal, size)) continue;
        captures[depth].start = start; captures[depth].length = n;
        depth++; positions[depth] = start + n + size; next[depth] = 0;
    }
    return 0;
}

static int menu_ru_pattern_allowed(unsigned role, unsigned id)
{
    if (id == 3030) return role == 12;
    if (!role) return 1;
    if (role == 5) return id == 1096 || id == 1109 || id == 1110 || id == 1112;
    if (role == 11) return id == 1449;
    if (role == 12) return id == 3010 || id == 3011 || id == 1383 ||
                           (id >= 3023 && id <= 3026) || id == 3030;
    return 0;
}

static unsigned menu_ru_argument_role(unsigned id, unsigned argument)
{
    if (argument == 0)
    {
        if (id == 81 || id == 93) return 1;
        if (id == 169) return 2;
        if (id == 3004) return 3;
        if (id == 700) return 4;
        if (id == 1133) return 5;
        if (id == 1167 || id == 3005) return 6;
        if (id == 1466) return 7;
        if (id == 1564) return 8;
        if (id == 1699) return 9;
        if (id == 1800) return 10;
        if (id == 885) return 13;
        if (id == 588 || id == 590 || id == 591 || id == 592) return 15;
        if (id == 1451) return 11;
        if (id == 1393 || id == 3014 || id == 1571 || id == 1572 || id == 1573) return 12;
    }
    if (id == 1243 && argument == 1) return 14;
    if (id == 3003 && argument == 2) return 3;
    return 0;
}

/* Known diagnostic labels may be concatenated; reason codes stay intact. */
static int menu_ru_memory_flags(const char *text, char *out, size_t capacity)
{
    const char *p=text;size_t used=0;unsigned count=0;
    while(*p && count++<5)
    {
        unsigned i;
        for(i=0;i<sizeof(menu_ru_aliases)/sizeof(menu_ru_aliases[0]);i++)
        {
            if(menu_ru_aliases[i].role!=13)continue;
            size_t n=strlen(menu_ru_aliases[i].en);
            if(!strncmp(p,menu_ru_aliases[i].en,n) && (!p[n] || p[n]==','))
            {
                if(!menu_ru_append(out,capacity,&used,menu_ru_aliases[i].ru,strlen(menu_ru_aliases[i].ru)))return 0;
                p+=n;break;
            }
        }
        if(i==sizeof(menu_ru_aliases)/sizeof(menu_ru_aliases[0]))return 0;
        if(*p==',')
        {
            if(!menu_ru_append(out,capacity,&used,p,1))return 0;
            p++;
        }
    }
    return !*p && count && strcmp(out,text);
}

static int menu_ru_compose(const char *text, char *out, size_t capacity,
                            unsigned role, unsigned depth);

static int menu_ru_build(const struct menu_ru_pattern *pattern, const char *text,
                          const struct menu_ru_capture captures[MENU_RU_MAX_ARGS],
                          char *out, size_t capacity, unsigned depth)
{
    /* The structural focus formats are not arbitrary string containers. */
    if (pattern->id == 3003)
    {
        unsigned n = captures[0].length;
        if (n > 1 || (n && text[captures[0].start] != '+' && text[captures[0].start] != '-')) return 0;
        const char *tail = text + captures[2].start;
        if (!((captures[2].length == 15 && !memcmp(tail, "steps from here", 15)) ||
              (captures[2].length == 6 && !memcmp(tail, "(here)", 6)))) return 0;
    }
    if (pattern->id == 3004 &&
        (captures[0].length != 11 || memcmp(text + captures[0].start, "Focus stack", 11))) return 0;
    size_t used = 0;
    if (!menu_ru_append(out, capacity, &used, pattern->ru[0], strlen(pattern->ru[0]))) return 0;
    for (unsigned i = 0; i < pattern->count; i++)
    {
        const char *value = text + captures[i].start;
        unsigned length = captures[i].length;
        unsigned role = menu_ru_argument_role(pattern->id, i);
        char argument[128], translated[128];
        if (role)
        {
            memcpy(argument, value, length); argument[length] = 0;
            for (unsigned j = 0; j < sizeof(menu_ru_aliases)/sizeof(menu_ru_aliases[0]); j++)
            {
                if (menu_ru_aliases[j].role == role && !strcmp(argument, menu_ru_aliases[j].en))
                {
                    value = menu_ru_aliases[j].ru; length = strlen(value); break;
                }
            }
            if (role == 13 && menu_ru_memory_flags(argument, translated, sizeof(translated)))
            {value = translated; length = strlen(value);}
            if (value == text + captures[i].start && depth == 0 &&
                (role == 5 || role == 11 || role == 12) &&
                menu_ru_compose(argument, translated, sizeof(translated), role, depth+1))
            {
                value = translated; length = strlen(value);
            }
        }
        if (!menu_ru_append(out, capacity, &used, value, length) ||
            !menu_ru_append(out, capacity, &used, pattern->ru[i+1], strlen(pattern->ru[i+1]))) return 0;
    }
    return 1;
}

static int menu_ru_magic_zoom(const char *text, char *out, size_t capacity)
{
    static const char * const triggers[] = {"HalfS, ","Focus, ","F+HS, ","ALW, "};
    static const char * const sizes[] = {"Small, ","Med, ","Large, ","FullScreen"};
    static const char * const positions[] = {"AFbox, ","TL, ","TR, ","BR, ","BL, "};
    const char *parts[5]; unsigned found = 0; const char *p = text;
    for (unsigned i=0;i<4;i++) if (!strncmp(p,triggers[i],strlen(triggers[i])))
    { parts[found++]=triggers[i];p+=strlen(triggers[i]);break; }
    if (!found) return 0;
    unsigned size;
    for (size=0;size<4;size++) if (!strncmp(p,sizes[size],strlen(sizes[size])))
    {parts[found++]=sizes[size];p+=strlen(sizes[size]);break;}
    if (size==4) return 0;
    char ratio[4];
    if (size==3) {if (*p) return 0;}
    else
    {
        unsigned i;
        for(i=0;i<5;i++)if(!strncmp(p,positions[i],strlen(positions[i])))
        {parts[found++]=positions[i];p+=strlen(positions[i]);break;}
        if(i==5 || p[0]<'1' || p[0]>'4' || p[1]!=':' || p[2]!='1') return 0;
        memcpy(ratio,p,3);ratio[3]=0;parts[found++]=ratio;p+=3;
        if(!strcmp(p,", Ss") || !strcmp(p,", Sz")) parts[found++]=p;
        else if(*p) return 0;
    }
    size_t used=0;
    for(unsigned i=0;i<found;i++)
    {
        const char *translated=menu_ru_lookup(parts[i]);
        if(!menu_ru_append(out,capacity,&used,translated,strlen(translated)))return 0;
    }
    return 1;
}

static int menu_ru_bad_settings(const char *text, char *out, size_t capacity)
{
    const char *p=text;size_t used=0;unsigned count=0;
    while(*p && count++<5)
    {
        unsigned i;
        for(i=0;i<sizeof(menu_ru_settings)/sizeof(menu_ru_settings[0]);i++)
        {
            size_t n=strlen(menu_ru_settings[i].en);
            if(!strncmp(p,menu_ru_settings[i].en,n) && (!p[n] || p[n]=='\n' || !strncmp(p+n,", ",2)))
            {
                if(!menu_ru_append(out,capacity,&used,menu_ru_settings[i].ru,strlen(menu_ru_settings[i].ru)))return 0;
                p+=n;break;
            }
        }
        if(i==sizeof(menu_ru_settings)/sizeof(menu_ru_settings[0]))return 0;
        size_t sep=*p=='\n'?1:!strncmp(p,", ",2)?2:0;
        if(sep && !menu_ru_append(out,capacity,&used,p,sep))return 0;
        p+=sep;
    }
    return !*p && count>0;
}

static int menu_ru_compose(const char *text, char *out, size_t capacity,
                            unsigned role, unsigned depth)
{
    if (!out || !capacity || depth>1) return 0;
    size_t length=strlen(text);
    if(length>MENU_RU_DISPLAY_LIMIT)return 0;
    /* Never reinterpret a translated argument or an arbitrary high-byte font. */
    for(unsigned i=0;i<length;i++)if((unsigned char)text[i]>=160)return 0;
    if(!role)
    {
        const char *exact=menu_ru_lookup(text);
        if(exact!=text)
        {
            size_t used=0;return menu_ru_append(out,capacity,&used,exact,strlen(exact));
        }
        if(menu_ru_magic_zoom(text,out,capacity))return 1;
        if(menu_ru_bad_settings(text,out,capacity))return 1;
        if(menu_ru_memory_flags(text,out,capacity))return 1;
    }
    struct menu_ru_capture captures[MENU_RU_MAX_ARGS];
    if(!length)return 0;
    unsigned first=(unsigned char)text[0];
    unsigned total=menu_ru_buckets[first].count+menu_ru_buckets[0].count;
    for(unsigned i=0;i<total;i++)
    {
        unsigned specific=menu_ru_buckets[first].count;
        unsigned slot=i<specific ? menu_ru_buckets[first].offset+i
                                 : menu_ru_buckets[0].offset+i-specific;
        const struct menu_ru_pattern *pattern=&menu_ru_patterns[menu_ru_order[slot]];
        /* Settings concatenations are validated as a whole above. */
        if(pattern->id>=1676 && pattern->id<=1685)continue;
        if(!menu_ru_pattern_allowed(role,pattern->id))continue;
        if(menu_ru_match(pattern,text,length,captures))
            return menu_ru_build(pattern,text,captures,out,capacity,depth) && strcmp(out,text);
    }
    return 0;
}
