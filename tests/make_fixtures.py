"""Generate small, deterministic test images. Pillow is only needed to regenerate."""

from pathlib import Path
import struct
import zlib
from PIL import Image
from PIL import ImageDraw

OUT = Path(__file__).with_name("fixtures")
OUT.mkdir(exist_ok=True)


def chunk(name, data):
    return (
        struct.pack(">I", len(data))
        + name
        + data
        + struct.pack(">I", zlib.crc32(name + data))
    )


def png(name, depth, color, rows, width=7, extra=b"", cgbi=False):
    data = b"".join(b"\0" + r for r in rows)
    data = zlib.compress(data)
    if cgbi:
        data = data[2:-4]
    result = b"\x89PNG\r\n\x1a\n"
    if cgbi:
        result += chunk(b"CgBI", b"\x40\xa0\x60\x82")
    result += chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, len(rows), depth, color, 0, 0, 0)
    )
    result += extra
    # Exercise split IDATs, including an empty chunk.
    for part in (data[:3], b"", data[3:]):
        result += chunk(b"IDAT", part)
    result += chunk(b"IEND", b"")
    (OUT / name).write_bytes(result)


for channels, color in ((1, 0), (2, 4), (3, 2), (4, 6)):
    for depth in (8, 16):
        rows = []
        for y in range(5):
            values = [
                ((x * 7651 + y * 179 + c * 9887) % 65536)
                for x in range(7)
                for c in range(channels)
            ]
            rows.append(
                bytes(v >> 8 for v in values)
                if depth == 8
                else struct.pack(">" + "H" * len(values), *values)
            )
        png(f"c{channels}-{depth}.png", depth, color, rows)
    im = Image.open(OUT / f"c{channels}-8.png")
    im.save(OUT / f"c{channels}.tga")
    if channels in (1, 3, 4):
        im.save(OUT / f"c{channels}.bmp")
    if channels in (1, 3):
        im.save(OUT / f"c{channels}.jpg", quality=93)
        im.save(OUT / f"c{channels}-progressive.jpg", quality=93, progressive=True)
        im.save(OUT / f"c{channels}.pnm")
    # Planar, uncompressed PSD composite.
    psd = (
        b"8BPS\0\1"
        + bytes(6)
        + struct.pack(">HIIHH", channels, 5, 7, 8, 1 if channels <= 2 else 3)
    )
    psd += bytes(14)
    raw = im.tobytes()
    psd += b"".join(raw[c::channels] for c in range(channels))
    (OUT / f"c{channels}.psd").write_bytes(psd)

rgb = Image.open(OUT / "c3-8.png")
rgb.convert("CMYK").save(OUT / "cmyk.jpg", quality=95)
rgb.save(OUT / "rle.tga", compression="tga_rle")
pal = rgb.quantize(16)
pal.save(OUT / "palette.png", transparency=bytes(range(0, 256, 16)))
pal.save(OUT / "still.gif", transparency=0)
frames = [
    rgb.convert("P", palette=Image.Palette.ADAPTIVE),
    rgb.transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert(
        "P", palette=Image.Palette.ADAPTIVE
    ),
]
frames[0].save(
    OUT / "animated.gif",
    save_all=True,
    append_images=frames[1:],
    duration=[70, 110],
    loop=0,
    disposal=2,
)
disposal = []
for i in range(4):
    frame = Image.new("RGB", (16, 12), "white")
    ImageDraw.Draw(frame).rectangle(
        (i * 3, i * 2, i * 3 + 2, i * 2 + 2), fill=(200, 0, 30)
    )
    disposal.append(frame)
disposal[0].save(
    OUT / "disposal3.gif",
    save_all=True,
    append_images=disposal[1:],
    duration=100,
    disposal=[1, 3, 3, 1],
    optimize=True,
)
animation = Image.open(OUT / "disposal3.gif")
expected = bytearray()
for i in range(animation.n_frames):
    animation.seek(i)
    expected += animation.convert("RGBA").tobytes()
(OUT / "disposal3.rgba").write_bytes(expected)
rgb.save(
    OUT / "animated.png",
    save_all=True,
    append_images=[rgb.transpose(Image.Transpose.FLIP_TOP_BOTTOM)],
    duration=100,
    loop=0,
)
for depth in (1, 2, 4):
    values = [
        bytes(((x * 73 + y * 11) & 255 for x in range((7 * depth + 7) // 8)))
        for y in range(5)
    ]
    png(f"grey-{depth}.png", depth, 0, values)
png(
    "rgb-trns.png",
    8,
    2,
    [rgb.tobytes()[y * 21 : (y + 1) * 21] for y in range(5)],
    extra=chunk(b"tRNS", struct.pack(">HHH", *rgb.getpixel((0, 0)))),
)
rgba = Image.open(OUT / "c4-8.png")
png(
    "iphone.png",
    8,
    6,
    [rgba.tobytes()[y * 28 : (y + 1) * 28] for y in range(5)],
    cgbi=True,
)
png("hidden-rgb.png", 8, 6, [bytes([12, 71, 93, 0, 84, 12, 99, 255])], width=2)
(OUT / "wide.png").write_bytes(
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", 0x7FFFFFFF, 2, 8, 6, 0, 0, 0))
)
(OUT / "tiny.hdr").write_bytes(
    b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 2 +X 2\n"
    + bytes([128, 64, 32, 129, 0, 0, 0, 0, 255, 128, 64, 130, 32, 128, 255, 128])
)
for c in (1, 3):
    values = [(x * 5413) % 65536 for x in range(7 * 5 * c)]
    (OUT / f"c{c}-16.pnm").write_bytes(
        (f"P{5 if c == 1 else 6}\n# test\n7 5\n65535\n").encode()
        + struct.pack(">" + "H" * len(values), *values)
    )
# Softimage PIC, one uncompressed RGB packet.
pic = (
    bytes.fromhex("5380f634")
    + bytes(84)
    + b"PICT"
    + struct.pack(">HH", 7, 5)
    + bytes(8)
)
pic += bytes([0, 8, 0, 0xE0]) + rgb.tobytes()
(OUT / "tiny.pic").write_bytes(pic)
(OUT / "low-max.pgm").write_bytes(b"P5\n3 2\n100\n" + bytes([0, 20, 40, 60, 80, 100]))
packed_tga = bytearray(18)
packed_tga[2], packed_tga[12], packed_tga[14] = 2, 8, 1
packed_tga[16], packed_tga[17] = 16, 32
(OUT / "packed16.tga").write_bytes(
    bytes(packed_tga) + struct.pack("<8H", 0, 1, 2, 3, 4, 7, 15, 31)
)
partial_gif = bytearray((OUT / "still.gif").read_bytes())
partial_gif[6:8] = struct.pack("<H", 9)
partial_gif[11] = 1
(OUT / "partial-background.gif").write_bytes(partial_gif)
print(f"generated {len(list(OUT.iterdir()))} fixtures")
