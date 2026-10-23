"""Compare public stb API results with the pinned upstream implementation."""

import ctypes as C
from pathlib import Path
import sys
import zlib

P = C.c_void_p
I = C.c_int
IP = C.POINTER(I)
READ = C.CFUNCTYPE(I, P, P, I)
SKIP = C.CFUNCTYPE(None, P, I)
EOF = C.CFUNCTYPE(I, P)


class Callbacks(C.Structure):
    _fields_ = [("read", READ), ("skip", SKIP), ("eof", EOF)]


class Library:
    def __init__(self, path):
        self.lib = C.CDLL(str(Path(path).resolve()))
        for base in ("stbi_load", "stbi_load_16", "stbi_loadf"):
            f = getattr(self.lib, base + "_from_memory")
            f.argtypes = [P, I, IP, IP, IP, I]
            f.restype = P
            f = getattr(self.lib, base + "_from_callbacks")
            f.argtypes = [C.POINTER(Callbacks), P, IP, IP, IP, I]
            f.restype = P
            f = getattr(self.lib, base)
            f.argtypes = [C.c_char_p, IP, IP, IP, I]
            f.restype = P
        for name in ("stbi_is_16_bit_from_memory", "stbi_is_hdr_from_memory"):
            getattr(self.lib, name).argtypes = [P, I]
        self.lib.stbi_info_from_memory.argtypes = [P, I, IP, IP, IP]
        self.lib.stbi_image_free.argtypes = [P]
        self.lib.stbi_failure_reason.restype = C.c_char_p
        self.lib.test_file.argtypes = [
            C.c_char_p,
            IP,
            IP,
            IP,
            I,
            C.POINTER(C.c_long),
            I,
        ]
        self.lib.test_file.restype = P
        self.lib.stbi_load_gif_from_memory.argtypes = [
            P,
            I,
            C.POINTER(P),
            IP,
            IP,
            IP,
            IP,
            I,
        ]
        self.lib.stbi_load_gif_from_memory.restype = P
        self.lib.stbi_zlib_decode_malloc_guesssize_headerflag.argtypes = [
            P,
            I,
            I,
            IP,
            I,
        ]
        self.lib.stbi_zlib_decode_malloc_guesssize_headerflag.restype = P
        for name in ("stbi_zlib_decode_buffer", "stbi_zlib_decode_noheader_buffer"):
            getattr(self.lib, name).argtypes = [P, I, P, I]

    def info(self, data):
        x, y, c = I(-1), I(-1), I(-1)
        ok = self.lib.stbi_info_from_memory(
            data, len(data), C.byref(x), C.byref(y), C.byref(c)
        )
        return (
            ok,
            x.value,
            y.value,
            c.value,
            self.lib.stbi_is_16_bit_from_memory(data, len(data)),
            self.lib.stbi_is_hdr_from_memory(data, len(data)),
        )

    def load(self, data, req, mode=0, source="memory", path=None, chunk=0):
        x, y, c, pos = I(-1), I(-1), I(-1), C.c_long(-1)
        base = ("stbi_load", "stbi_load_16", "stbi_loadf")[mode]
        if source == "memory":
            ptr = getattr(self.lib, base + "_from_memory")(
                data, len(data), C.byref(x), C.byref(y), C.byref(c), req
            )
        elif source == "filename":
            ptr = getattr(self.lib, base)(
                str(path).encode(), C.byref(x), C.byref(y), C.byref(c), req
            )
        elif source == "file":
            ptr = self.lib.test_file(
                str(path).encode(),
                C.byref(x),
                C.byref(y),
                C.byref(c),
                req,
                C.byref(pos),
                mode,
            )
        else:
            cursor = [0]

            def read(_, dst, n):
                n = min(n, len(data) - cursor[0], chunk or n)
                C.memmove(dst, data[cursor[0] : cursor[0] + n], n)
                cursor[0] += n
                return n

            def skip(_, n):
                cursor[0] += n
                assert 0 <= cursor[0] <= len(data)

            cb = Callbacks(
                READ(read), SKIP(skip), EOF(lambda _: int(cursor[0] >= len(data)))
            )
            ptr = getattr(self.lib, base + "_from_callbacks")(
                C.byref(cb), None, C.byref(x), C.byref(y), C.byref(c), req
            )
            pos.value = cursor[0]
        if not ptr:
            return None
        count = x.value * y.value * (req or c.value)
        raw = C.string_at(ptr, count * (1, 2, 4)[mode])
        self.lib.stbi_image_free(ptr)
        return x.value, y.value, c.value, raw, pos.value


def equivalent(actual, expected, name, mode=0, check_position=False):
    assert (actual is None) == (expected is None), f"{name}: success mismatch"
    if actual is None:
        return
    assert (
        actual[:3] == expected[:3]
    ), f"{name}: shape/channels {actual[:3]} != {expected[:3]}"
    # JPEG IDCT, chroma interpolation and CMYK conversion are decoder-specific.
    # These tests require exact output for every lossless format and for C/C++.
    if ".jpg" not in name and ".jpeg" not in name:
        assert actual[3] == expected[3], f"{name}: pixels differ (mode {mode})"
    if check_position:
        assert (
            actual[4] == expected[4]
        ), f"{name}: file position {actual[4]} != {expected[4]}"


def main():
    adapter, reference, cpp = [Library(p) for p in sys.argv[1:4]]
    paths = []
    for directory in sys.argv[4:]:
        paths += sorted(
            p
            for p in Path(directory).rglob("*")
            if p.suffix.lower()
            in {
                ".png",
                ".apng",
                ".bmp",
                ".gif",
                ".jpeg",
                ".jpg",
                ".tga",
                ".pnm",
                ".pgm",
                ".ppm",
                ".hdr",
                ".psd",
                ".pic",
            }
        )
    count = 0
    failures = []
    for path in paths:
        data = path.read_bytes()
        if len(data) > 3_000_000:
            continue
        try:
            assert adapter.info(data) == reference.info(data), f"{path.name}: metadata"
            for flip in (0, 1):
                for lib in (adapter, reference, cpp):
                    lib.lib.stbi_set_flip_vertically_on_load(flip)
                for req in range(5):
                    for mode in range(3):
                        expected = reference.load(data, req, mode)
                        actual = adapter.load(data, req, mode)
                        equivalent(actual, expected, path.name, mode)
                        other = cpp.load(data, req, mode)
                        assert actual == other, f"{path.name}: C/C++ differ"
                        if flip == 0:
                            for source in ("callbacks", "file", "filename"):
                                actual = adapter.load(data, req, mode, source, path)
                                expected = reference.load(data, req, mode, source, path)
                                equivalent(
                                    actual,
                                    expected,
                                    path.name,
                                    mode,
                                    check_position=(source == "file" and mode != 2),
                                )
                                count += 1
                        count += 2
            for lib in (adapter, reference, cpp):
                assert (
                    lib.lib.test_live_allocations() == 0
                ), f"{path.name}: allocation leak"
        except AssertionError as e:
            failures.append(str(e))
    for lib in (adapter, reference, cpp):
        lib.lib.stbi_set_flip_vertically_on_load(0)
    # Public deflate helpers, fixed destination and growing destination.
    for data in (b"", b"hello" * 3000, bytes(range(256)) * 100):
        compressed = zlib.compress(data)
        for header in (0, 1):
            src = compressed if header else compressed[2:-4]
            for lib in (adapter, reference, cpp):
                n = I(-1)
                ptr = lib.lib.stbi_zlib_decode_malloc_guesssize_headerflag(
                    src, len(src), 1, C.byref(n), header
                )
                assert ptr and C.string_at(ptr, n.value) == data
                lib.lib.stbi_image_free(ptr)
                dst = C.create_string_buffer(max(1, len(data)))
                fn = (
                    lib.lib.stbi_zlib_decode_buffer
                    if header
                    else lib.lib.stbi_zlib_decode_noheader_buffer
                )
                assert fn(dst, len(data), src, len(src)) == len(data)
                assert dst.raw[: len(data)] == data
                count += 2
    hits = [adapter.lib.test_native_hits(i) for i in range(1, 7)]
    print(
        f"{len(paths)} images; {count} comparisons; Wuffs PNG/BMP/GIF/JPEG/PNM/TGA hits: {hits}"
    )
    if failures:
        print("\n".join(failures[:40]))
        raise SystemExit(f"{len(failures)} failing images")
    assert all(hits), "a native decoder was never exercised"
    print("PASS: API differential tests")


if __name__ == "__main__":
    main()
