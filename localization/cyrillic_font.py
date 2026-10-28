"""Build one-bit Cyrillic on the original RBF Latin grid and baseline."""
from PIL import Image, ImageDraw, ImageFont

# These upright glyphs have the same shape in the two alphabets.
LATIN_SHAPES = dict(zip('АВЕКМНОРСТХаеорсух', 'ABEKMHOPCTXaeopcyx'))


def bitmap(data, header, code):
    stride = header[3] // header[5]
    start = header[11] + (code - header[7]) * header[3]
    result = Image.new('1', (stride * 8, header[5]))
    for y in range(header[5]):
        for x in range(stride * 8):
            if data[start+y*stride+x//8] & (1 << (x % 8)):
                result.putpixel((x, y), 1)
    return result


def pack(image, charsize):
    stride = charsize // image.height
    result = bytearray(charsize)
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x, y)):
                result[y*stride+x//8] |= 1 << (x % 8)
    return result


def make_cyrillic(data, header, letters, filename):
    height = header[5]
    stride = header[3] // height
    cell_width = min(header[6], stride * 8)
    mono = filename.startswith('term')
    original = {c: bitmap(data, header, ord(c)) for c in 'HxpNEe'}
    cap = original['H'].getbbox()
    lower = original['x'].getbbox()
    desc = original['p'].getbbox()
    baseline = cap[3]  # Exclusive lower bound: all ordinary letters end here.
    cap_height = baseline - cap[1]
    x_height = baseline - lower[1]
    descent = desc[3] - baseline
    advance = lambda c: data[header[10]+ord(c)-header[7]]
    mono_width = advance('H')
    face = '/usr/share/fonts/TTF/DejaVuSansMono.ttf' if mono else '/usr/share/fonts/TTF/DejaVuSans.ttf'

    def native(c, font):
        canvas = Image.new('1', (height*6, height*6))
        anchor = height*3
        ImageDraw.Draw(canvas).text((height, anchor), c, font=font, fill=1, anchor='ls')
        return canvas, anchor

    # Select a hinted pixel size by the actual Latin bitmap heights, rather
    # than shrinking the alphabet until its accents fit the entire RBF cell.
    candidates = []
    for size in range(5, height*2+1):
        font = ImageFont.truetype(face, size)
        h_img, _ = native('H', font)
        x_img, _ = native('x', font)
        hb, xb = h_img.getbbox(), x_img.getbbox()
        score = 3*abs(hb[3]-hb[1]-cap_height) + 2*abs(xb[3]-xb[1]-x_height)
        candidates.append((score, abs(size-height), size, font))
    _, _, size, font = min(candidates, key=lambda item: item[:3])

    widths, glyphs = [], bytearray()
    made = {}
    for c in letters:
        if c in LATIN_SHAPES:
            source = LATIN_SHAPES[c]
            image = bitmap(data, header, ord(source))
            width = advance(source)
        elif c in 'ЁёЙй':
            base = {'Ё': 'Е', 'ё': 'е', 'Й': 'И', 'й': 'и'}[c]
            image, width = made[base][0].copy(), made[base][1]
            box = image.getbbox()
            if box[1] < 2:
                # Tiny/cropped original fonts have no accent reserve. Keep
                # the baseline, make two top rows available for mark + gap.
                body = image.crop(box)
                image = Image.new('1', image.size)
                image.paste(body.resize((body.width, baseline-2), Image.Resampling.NEAREST), (box[0], 2))
                box = image.getbbox()
            available = box[1]
            mark_height = min(2, max(1, available-1))
            y0 = max(0, box[1]-mark_height-1)
            center = (box[0]+box[2]-1)//2
            draw = ImageDraw.Draw(image)
            if c in 'Ёё':
                dot = 1 if height < 24 else 2
                separation = max(2, (box[2]-box[0])//3)
                for x in (center-separation//2, center+(separation+1)//2):
                    draw.rectangle((x, y0, x+dot-1, y0+mark_height-1), fill=1)
            elif mark_height == 1:
                draw.line((center-1, y0, center+1, y0), fill=1)
            else:
                draw.point((center-2, y0), fill=1)
                draw.point((center+2, y0), fill=1)
                draw.line((center-1, y0+1, center+1, y0+1), fill=1)
        elif c == 'И':
            image = original['N'].copy()
            box = image.getbbox()
            image.paste(image.crop(box).transpose(Image.Transpose.FLIP_LEFT_RIGHT), box[:2])
            width = advance('N')
        else:
            source, anchor = native(c, font)
            box = source.getbbox()
            body = source.crop((box[0], box[1], box[2], anchor))
            ink = body.getbbox()
            body = body.crop((0, ink[1], body.width, ink[3]))
            body_height = cap_height if c.isupper() or c in 'бф' else x_height
            # Preserve a shared baseline while fitting natural descenders into
            # the same descender area used by original Latin p/y.
            below = 0
            if c in 'ф':
                below = descent
            elif c in 'ДЦЩдцщ':
                below = max(1, (descent+1)//2)
            image = Image.new('1', (stride*8, height))
            max_ink = mono_width if mono else cell_width-cap[0]-1
            ink_width = min(body.width, max_ink)
            left = (mono_width-ink_width)//2 if mono else cap[0]
            body = body.resize((ink_width, body_height), Image.Resampling.NEAREST)
            image.paste(body, (left, baseline-body_height))
            if below and box[3] > anchor:
                tail = source.crop((box[0], anchor, box[2], box[3]))
                image.paste(tail.resize((ink_width, below), Image.Resampling.NEAREST), (left, baseline))
            width = mono_width if mono else min(cell_width, left+ink_width+1)
        if mono:
            width = mono_width
        assert image.getbbox() and image.getbbox()[2] <= width, (filename, c)
        made[c] = image, width
        widths.append(width)
        glyphs.extend(pack(image, header[3]))
    return widths, glyphs, {'size': size, 'baseline': baseline-1,
                            'cap_top': cap[1], 'x_top': lower[1],
                            'mono': mono, 'advance': mono_width}
