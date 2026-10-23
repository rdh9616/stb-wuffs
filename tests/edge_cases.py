"""Regression tests for state, ownership, allocation failures and animation."""

import ctypes as C
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sys
from threading import Barrier, Lock
import zlib
from differential import Library, I, P, equivalent

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def gif(lib, data, req):
    x, y, z, c, delays = I(), I(), I(), I(), P()
    ptr = lib.lib.stbi_load_gif_from_memory(
        data,
        len(data),
        C.byref(delays),
        C.byref(x),
        C.byref(y),
        C.byref(z),
        C.byref(c),
        req,
    )
    if not ptr:
        return None
    pixels = C.string_at(ptr, x.value * y.value * z.value * (req or c.value))
    times = C.string_at(delays, z.value * 4) if delays else None
    lib.lib.stbi_image_free(ptr)
    lib.lib.stbi_image_free(delays)
    return x.value, y.value, z.value, c.value, pixels, times


def main():
    a, r = Library(sys.argv[1]), Library(sys.argv[2])
    declarations = (
        (ROOT / "vendor/stb_image.h")
        .read_text(encoding="utf-8")
        .split("#ifdef STB_IMAGE_IMPLEMENTATION")[0]
    )
    names = sorted(set(re.findall(r"STBIDEF\s+[^;]+?\b(stbi_\w+)\s*\(", declarations)))
    for name in names:
        if name != "stbi_convert_wchar_to_utf8":
            getattr(a.lib, name)
    print(
        f"API exports: {len(names)-1} standard functions present (UTF-8 helper tested by build matrix)"
    )
    # Animation conversion and vertical flipping must use the output stride.
    data = (FIXTURES / "animated.gif").read_bytes()
    for req in range(5):
        normal = gif(a, data, req)
        assert normal == gif(r, data, req)
        a.lib.stbi_set_flip_vertically_on_load(1)
        flipped = gif(a, data, req)
        a.lib.stbi_set_flip_vertically_on_load(0)
        x, y, z, _, pixels, _ = normal
        row = x * (req or 4)
        expected = b"".join(
            pixels[(f * y + j) * row : (f * y + j + 1) * row]
            for f in range(z)
            for j in reversed(range(y))
        )
        assert flipped[4] == expected
    disposal = gif(a, (FIXTURES / "disposal3.gif").read_bytes(), 4)
    assert disposal[4] == (FIXTURES / "disposal3.rgba").read_bytes(), "GIF disposal 3"
    # Force each allocation site to fail; every returned allocation is freed.
    cases = [
        "c4-8.png",
        "c4-16.png",
        "c3.jpg",
        "c4.bmp",
        "c3.tga",
        "c3.psd",
        "still.gif",
        "iphone.png",
    ]
    count = 0
    a.lib.stbi_set_flip_vertically_on_load(1)
    for name in cases:
        data = (FIXTURES / name).read_bytes()
        for mode in range(3):
            for source in ("memory", "callbacks"):
                for after in range(30):
                    a.lib.test_fail_allocation(after)
                    a.load(data, 2, mode, source)
                    a.lib.test_fail_allocation(-1)
                    assert (
                        a.lib.test_live_allocations() == 0
                    ), f"leak: {name}/{mode}/{source}/{after}"
                    count += 1
    a.lib.stbi_set_flip_vertically_on_load(0)
    print(f"Allocation failure paths: {count}, zero outstanding allocations")
    # A valid PNG survives tiny callback reads; malformed input returns failure.
    for name in ("c4-8.png", "c3.jpg", "c3.tga", "still.gif", "c3.pnm"):
        data = (FIXTURES / name).read_bytes()
        expected = a.load(data, 4)
        for chunk in (1, 3, 7):
            equivalent(a.load(data, 4, source="callbacks", chunk=chunk), expected, name)
    data = (FIXTURES / "c4-8.png").read_bytes()
    for end in range(len(data)):
        equivalent(
            a.load(data[:end], 4), r.load(data[:end], 4), f"truncated PNG at {end}"
        )
    # File probes preserve offsets, even when metadata or decoding fails.
    for name in ("c4-8.png", "c4-16.png", "tiny.hdr", "wide.png"):
        for mode in range(3, 6):
            x, y, c, pos = I(), I(), I(), C.c_long()
            a.lib.test_file(
                str(FIXTURES / name).encode(),
                C.byref(x),
                C.byref(y),
                C.byref(c),
                0,
                C.byref(pos),
                mode,
            )
            assert pos.value == 0
    # Original settings apply to compatibility and Wuffs routes alike.
    for name in (
        "stbi_ldr_to_hdr_gamma",
        "stbi_ldr_to_hdr_scale",
        "stbi_hdr_to_ldr_gamma",
        "stbi_hdr_to_ldr_scale",
    ):
        for lib in (a, r):
            getattr(lib.lib, name).argtypes = [C.c_float]
            getattr(lib.lib, name)(1.7)
    for name, mode in (("c4-8.png", 2), ("tiny.hdr", 0)):
        data = (FIXTURES / name).read_bytes()
        equivalent(a.load(data, 2, mode), r.load(data, 2, mode), name, mode)
    data = (FIXTURES / "iphone.png").read_bytes()
    for convert in (0, 1):
        for unpremul in (0, 1):
            for lib in (a, r):
                lib.lib.stbi_convert_iphone_png_to_rgb(convert)
                lib.lib.stbi_set_unpremultiply_on_load(unpremul)
            equivalent(a.load(data, 4), r.load(data, 4), "iphone")
    # Exercise the remaining public zlib allocation entry points.
    payload = b"compatibility" * 20
    src = zlib.compress(payload)
    for name, args in (
        ("stbi_zlib_decode_malloc", [src, len(src)]),
        ("stbi_zlib_decode_malloc_guesssize", [src, len(src), 1]),
        ("stbi_zlib_decode_noheader_malloc", [src[2:-4], len(src) - 6]),
    ):
        fn = getattr(a.lib, name)
        fn.argtypes = [P] + [I] * (len(args) - 1) + [C.POINTER(I)]
        fn.restype = P
        length = I()
        ptr = fn(*args, C.byref(length))
        assert ptr and C.string_at(ptr, length.value) == payload
        a.lib.stbi_image_free(ptr)
    # Synchronize TLS setting, then serialize decoding around test-only counters.
    barrier, lock = Barrier(2), Lock()
    data = (FIXTURES / "c4-8.png").read_bytes()

    def worker(flip):
        a.lib.stbi_set_flip_vertically_on_load_thread(flip)
        barrier.wait()
        with lock:
            return a.load(data, 4)[3]

    with ThreadPoolExecutor(2) as pool:
        rows = list(pool.map(worker, (0, 1)))
    row = 7 * 4
    assert rows[1] == b"".join(
        rows[0][i * row : (i + 1) * row] for i in reversed(range(5))
    )
    assert a.lib.test_live_allocations() == 0
    print("PASS: animation, callbacks, truncation, probes, settings, zlib and TLS")


if __name__ == "__main__":
    main()
