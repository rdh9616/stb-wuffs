"""Reproducibly insert the Wuffs backend into pinned stb_image 2.30."""

from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def generate():
    manifest = json.loads((ROOT / "vendor/manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        actual = hashlib.sha256((ROOT / "vendor" / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Pinned dependency changed: {name}")
    stb = (ROOT / "vendor/stb_image.h").read_text(encoding="utf-8")
    # stb assumes one callback call fills the requested span. Aggregate short
    # reads so format probing can rewind within its original 128-byte buffer.
    marker = "static void stbi__refill_buffer(stbi__context *s);"
    assert stb.count(marker) == 1
    reader = """static int stbi__wuffs_read(stbi__context *s, char *dst, int size)
{
   int total = 0;
   while (total < size) {
      int n = s->io.read(s->io_user_data, dst + total, size - total);
      if (n <= 0 || n > size - total) break;
      total += n;
   }
   return total;
}

"""
    stb = stb.replace("(s->io.read)(s->io_user_data,", "stbi__wuffs_read(s,")
    stb = stb.replace(marker, reader + marker)
    marker = "static void stbi__start_mem(stbi__context *s, stbi_uc const *buffer, int len)\n{"
    assert stb.count(marker) == 1
    stb = stb.replace(
        marker,
        marker
        + "\n   static const stbi_uc empty = 0;\n   if (!buffer || len < 0) { buffer = &empty; len = 0; }",
    )
    # Correct narrowly scoped upstream safety defects without changing the API.
    fixes = {
        "stbi__vertical_flip_slices( result, *x, *y, *z, *comp );": "if (result) stbi__vertical_flip_slices(result, *x, *y, *z, req_comp ? req_comp : 4);",
        "two_back = out - 2 * stride;": "two_back = out + (layers - 2) * stride;",
        "memcpy( &g->out[pi * 4], &two_back[pi * 4], 4 );": "memcpy( &g->out[pi * 4], &g->background[pi * 4], 4 );",
        'if (reduced == NULL) return stbi__errpuc("outofmem", "Out of memory");': 'if (reduced == NULL) { STBI_FREE(orig); return stbi__errpuc("outofmem", "Out of memory"); }',
        'if (enlarged == NULL) return (stbi__uint16 *) stbi__errpuc("outofmem", "Out of memory");': 'if (enlarged == NULL) { STBI_FREE(orig); return (stbi__uint16 *) stbi__errpuc("outofmem", "Out of memory"); }',
        "z->img_comp[i].data = (stbi_uc*) (((size_t) z->img_comp[i].raw_data + 15) & ~15);": "z->img_comp[i].data = (stbi_uc*) (((size_t) z->img_comp[i].raw_data + 15) & ~15);\n"
        "      memset(z->img_comp[i].data, 0, (size_t)z->img_comp[i].w2 * z->img_comp[i].h2);",
    }
    for old, new in fixes.items():
        assert stb.count(old) == 1, old
        stb = stb.replace(old, new)
    stb = stb.replace(
        "ri.bits_per_channel = 8;\n   }",
        "ri.bits_per_channel = 8;\n      if (!result) return NULL;\n   }",
    )
    stb = stb.replace(
        "ri.bits_per_channel = 16;\n   }",
        "ri.bits_per_channel = 16;\n      if (!result) return NULL;\n   }",
    )
    # The PNM-only upstream build needs the same 16-bit conversion helpers.
    stb = stb.replace(
        "#if defined(STBI_NO_PNG) && defined(STBI_NO_PSD)\n",
        "#if defined(STBI_NO_PNG) && defined(STBI_NO_PSD) && defined(STBI_NO_PNM)\n",
    )
    stb = stb.replace(
        "static int stbi__is_16_main(stbi__context *s)\n{",
        "static int stbi__is_16_main(stbi__context *s)\n{\n   STBI_NOTUSED(s);",
    )
    signature = "static void *stbi__load_main(stbi__context *s, int *x, int *y, int *comp, int req_comp, stbi__result_info *ri, int bpc)"
    assert stb.count(signature) == 1
    stb = stb.replace(
        signature,
        signature
        + ";\n\n"
        + signature.replace("stbi__load_main", "stbi__wuffs_fallback"),
    )
    end = "#endif // STB_IMAGE_IMPLEMENTATION"
    assert stb.count(end) == 1
    config = (ROOT / "src/wuffs_config.h").read_text(encoding="utf-8")
    wuffs = (ROOT / "vendor/wuffs-v0.4.c").read_text(encoding="utf-8")
    # This Wuffs release leaves initializer/allocator/sizeof helpers external
    # even with STATIC_FUNCTIONS. Internalize their declarations and definitions
    # so STB_IMAGE_STATIC works in multiple translation units.
    pattern = r"(?m)^((?:wuffs_base__status WUFFS_BASE__WARN_UNUSED_RESULT|size_t|wuffs_[a-z0-9_]+\*)\n)((?:wuffs_[a-z0-9_]+__(?:initialize|alloc)|sizeof__wuffs_[a-z0-9_]+)\()"
    wuffs, count = re.subn(pattern, r"static \1\2", wuffs)
    assert count > 100, count
    constants = re.findall(r"(?m)^extern const char (wuffs_\w+)\[\];", wuffs)
    for name in constants:
        match = re.search(r"(?m)^const char " + name + r"\[\]\s*=\s*[^;]+;", wuffs)
        assert match, name
        definition = match.group()
        wuffs = wuffs.replace(definition, "", 1)
        wuffs = wuffs.replace(
            "extern const char " + name + "[];", "static " + definition, 1
        )
    for declaration, typ, name, length in re.findall(
        r"(?m)^(extern const (uint\d+_t) (wuffs_\w+)\[(\d+)\];)", wuffs
    ):
        match = re.search(
            r"(?m)^const " + typ + " " + name + r"\[" + length + r"\]\s*=\s*\{[^;]+;",
            wuffs,
        )
        assert match, name
        definition = match.group()
        wuffs = wuffs.replace(definition, "", 1)
        wuffs = wuffs.replace(declaration, "static " + definition, 1)
    # Private status strings and vtables have no forward declarations.
    wuffs = re.sub(
        r"(?m)^const (char wuffs_\w+\[\]|wuffs_\w+\s+\w+__func_ptrs_for__\w+)",
        r"static const \1",
        wuffs,
    )
    backend = (ROOT / "src/wuffs_backend.h").read_text(encoding="utf-8")
    stb = stb.replace(
        end,
        config.replace("/* WUFFS_AMALGAMATION */", wuffs) + "\n" + backend + "\n" + end,
    )
    banner = "/* stb-wuffs: generated by tools/amalgamate.py. See README.md and vendor/manifest.json.\n   Full stb_image 2.30 API; Wuffs decoders with stb compatibility fallback.\n\n"
    banner += (
        (ROOT / "LICENSE").read_text(encoding="utf-8")
        + "\nWuffs MIT license:\n"
        + (ROOT / "vendor/WUFFS-LICENSE-MIT").read_text(encoding="utf-8")
        + "\n*/\n"
    )
    return (banner + stb).encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = generate()
    target = ROOT / "stb_image.h"
    if args.check:
        assert target.read_bytes() == output, "stb_image.h is stale"
        print("amalgamation: reproducible")
    else:
        target.write_bytes(output)
        print(f"wrote {target.name}: {len(output)} bytes")
