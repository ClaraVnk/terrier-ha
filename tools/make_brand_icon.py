"""The integration's brand icon: the object itself, cut out of its photograph.

Home Assistant serves an integration's icon from `custom_components/<domain>/
brand/` since 2026.3 — local images take priority over the brands CDN, so
this is the whole of it and there is nothing to submit anywhere.

Eight hand-drawn attempts came before this one and every one was worse than
the thing it was drawing: too flat to read, a face that turned the silhouette
into a cartoon, a head that looked like somebody else's character, and one
that simply looked like the neighbours' mark. The project has had a
photograph of a Nabaztag since its first commit. That is the icon.

Run it as:
    python tools/make_brand_icon.py nabaztag.jpg custom_components/terrier/brand
"""

import sys

from PIL import Image, ImageFilter

SRC = sys.argv[1] if len(sys.argv) > 1 else "nabaztag.jpg"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."

WHITE = 243  # a pixel at least this bright may be background


def cutout(path: str) -> Image.Image:
    """Alpha from a flood of the background, not from a brightness threshold.

    The subject is a white plastic rabbit photographed on white. A threshold
    makes its own body semi-transparent — the violet tile showed straight
    through it. What separates subject from background here is not brightness
    but *connection to the edge of the frame*: the paper touches the border,
    the rabbit does not.
    """
    from collections import deque

    im = Image.open(path).convert("RGB")
    w, h = im.size
    grey = im.convert("L").load()

    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if grey[x, y] >= WHITE and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if grey[x, y] >= WHITE and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < w
                and 0 <= ny < h
                and not bg[ny * w + nx]
                and grey[nx, ny] >= WHITE
            ):
                bg[ny * w + nx] = 1
                q.append((nx, ny))

    alpha = Image.frombytes("L", (w, h), bytes(0 if v else 255 for v in bg))
    # The raised ear's tip is a specular highlight blown to pure 255 — the
    # same value as the paper — so the flood walks straight into it and bites
    # a notch out of the ear. No threshold can separate them; they are the
    # same colour. A morphological closing can: dilate, then erode by the
    # same amount, which fills any gap narrower than the kernel and leaves
    # the silhouette where it was.
    alpha = alpha.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.MinFilter(21))
    # Then pull the edge in by a pixel and soften it, so no white halo
    # survives against the tile.
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(alpha)
    return im


VIOLET = (139, 92, 246, 255)


def square(im: Image.Image, size: int) -> Image.Image:
    im = im.crop(im.getbbox())
    side = max(im.size)
    pad = Image.new("RGBA", (side, side), (0, 0, 0, 0))

    # Centre the BODY, not the bounding box. One ear is flopped out sideways,
    # so the box reaches much further on that side and centring it leaves the
    # rabbit visibly sitting to the right — thirteen pixels at 256, which is
    # plainly visible once somebody points at it. The eye centres on the base
    # of the bell, so that is what gets centred.
    a = im.getchannel("A").load()
    base = im.height - 1
    rows = [
        x
        for y in range(max(0, base - 14), base + 1)
        for x in range(im.width)
        if a[x, y] > 120
    ]
    body_cx = (min(rows) + max(rows)) // 2 if rows else im.width // 2
    pad.alpha_composite(im, (side // 2 - body_cx, (side - im.height) // 2))
    # A little air, the way brands renders everything else.
    # On a tile, in the warren's violet. A white rabbit on transparent is
    # invisible against Home Assistant's own light surfaces — and the violet
    # is the project's accent everywhere else, down to the colour the rabbit
    # breathes in out of the box.
    from PIL import ImageDraw

    F = 4
    big = size * F
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle(
        [0, 0, big - 1, big - 1], radius=int(big * 0.22), fill=VIOLET
    )
    inner = int(big * 0.82)
    out.alpha_composite(
        pad.resize((inner, inner), Image.LANCZOS),
        ((big - inner) // 2, (big - inner) // 2),
    )
    return out.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    cut = cutout(SRC)
    square(cut, 256).save(f"{OUT}/icon.png")
    square(cut, 512).save(f"{OUT}/icon@2x.png")
    print("ok")
