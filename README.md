# stb-wuffs

A single-header **stb_image 2.30 API adapter backed by Wuffs**, with stb compatibility fallbacks. Copy `stb_image.h` into your project and use the usual API:

```c
// In exactly one C or C++ translation unit:
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

// Elsewhere, include it without STB_IMAGE_IMPLEMENTATION.
int width, height, source_channels;
unsigned char *pixels = stbi_load("image.png", &width, &height, &source_channels, 4);
if (pixels) {
    // pixels contains width * height RGBA pixels.
    stbi_image_free(pixels);
}
```

No Wuffs compiler, Go toolchain, external image libraries, or runtime downloads are required. The generated header includes the pinned Wuffs C implementation. Use C99 or later, or C++11 or later; MSVC builds use `/std:c11`. Unix programs using the floating-point APIs may need `-lm`.

## Compatibility contract

The complete upstream public API is retained: 8-bit, 16-bit and floating-point loads; filenames, `FILE*`, memory and callbacks; metadata and format probes; animated GIFs and delays; allocation hooks; global and thread-local options; HDR/LDR conversion settings; iPhone PNG handling; and the six public zlib/deflate functions. Source channel counts and requested channels follow stb conventions. `STB_IMAGE_IMPLEMENTATION`, `STB_IMAGE_STATIC`, `STBIDEF`, `STBI_ONLY_*`, `STBI_NO_*`, `STBI_MAX_DIMENSIONS`, and allocator configuration remain available.

| Input / API | Decoder path |
| --- | --- |
| Ordinary 8-bit PNG, BMP, GIF first frame, JPEG, PGM/PPM, TGA | Wuffs, with stb channel conversion semantics |
| 16-bit source images | stb, preserving source precision |
| HDR, PSD, Softimage PIC | stb |
| Animated-GIF all-frames API | stb, with disposal and flip fixes |
| APNG default image, color-key PNG transparency, BMP alpha, partial first GIF frames, packed RGB TGA, CgBI, Wuffs rejections | stb compatibility fallback |
| Metadata, probes and zlib/deflate helper APIs | stb |

The aim is **complete API and format coverage**, not a promise that two independent decoders produce identical results on every possible byte stream. JPEG IDCT, chroma interpolation, CMYK conversion and incomplete progressive scans can produce different pixel values. Define `STBI_WUFFS_EXACT_JPEG` to retain stb's JPEG decoder. Malformed inputs can also have decoder-specific behavior. Error strings are diagnostic text, not a stable protocol.

This is a hybrid implementation: it does **not** remove all stb decoders or give the whole adapter Wuffs' memory-safety guarantees. It does not add Wuffs-only formats such as WebP to the stb API. Wuffs' upstream partial stb replacement is not enabled because it does not supply this complete API surface.

## Configuration and integration

```c
#define STBI_NO_STDIO           // Optional: memory and callbacks only.
#define STBI_ONLY_PNG           // Optional: only PNG decoding.
#define STBI_WUFFS_EXACT_JPEG    // Optional: stb's JPEG pixel arithmetic.
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
```

- `STBI_MALLOC`, `STBI_REALLOC` or `STBI_REALLOC_SIZED`, and `STBI_FREE` govern adapter allocations, including Wuffs decoder objects, work buffers, output and replay buffers.
- `STBI_NO_SIMD` disables architecture-specific Wuffs code as well as stb SIMD code.
- `STBI_WUFFS_DISABLE` selects the stb implementation while retaining the documented fixes below. It is useful for diagnosis.
- `STBI_WUFFS_ON_DECODE(kind)` is an optional instrumentation macro. It runs only after successful Wuffs decoding: PNG=1, BMP=2, GIF=3, JPEG=4, PNM=5, TGA=6. It adds no public function.
- Compile another Wuffs implementation in a separate translation unit. Wuffs internals in this header have private linkage, including in multi-translation-unit `STB_IMAGE_STATIC` builds. Wuffs preprocessor names are not a supported public configuration surface of this adapter.
- Callback `read` may return short reads. A zero or negative return ends that read attempt; this synchronous API does not wait for asynchronous input. The callback must never write more bytes than requested.
- Callback `skip` must support negative values to return unread lookahead, as specified by stb's callback interface. The adapter retains compressed input read during the Wuffs attempt so it can replay fallback decoding without rewinding the entire source. This costs O(compressed bytes read) additional memory for callback/file inputs. Memory inputs are read directly. There is no read-until-EOF requirement.
- `stbi_info_from_file`, HDR probes and 16-bit probes preserve the file offset. Successful 8-bit and 16-bit file loading leaves the offset after the consumed image; PNG loading consumes through IEND. Floating-point file loading retains the compatibility implementation's behavior, except that successful Wuffs decoding returns unused lookahead.
- Global setters have stb's original concurrency restrictions. Thread-local setters and failure state use stb's existing TLS support.

## Pinned dependencies

| Library | Version | Commit |
| --- | --- | --- |
| [stb](https://github.com/nothings/stb) | stb_image 2.30 | `003501f6d7a8668ce8b6d875e34dd97ad0d5d5b5` |
| [Wuffs](https://github.com/google/wuffs) | 0.4.0-alpha.12+4048.20261020 | `4be865da258c4b5e6d3e716fd4f36be016496a46` |

Wuffs 0.4 is an **alpha** dependency, selected for its current decoder coverage, including JPEG. It is vendored and hash-pinned; no dependency is fetched during a normal build. `vendor/manifest.json` records the source hashes. Consult the [Wuffs releases documentation](https://github.com/google/wuffs/blob/4be865da258c4b5e6d3e716fd4f36be016496a46/release/c/README.md) before choosing a different release.

## Build and test

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel 3
ctest --test-dir build -C Release --output-on-failure
```

Python 3 is needed only for development tests and header generation. Test fixtures are committed; Pillow is needed only to regenerate them using `tests/make_fixtures.py`. The application itself has no Python dependency.

Tests compare C and C++ builds with the unmodified pinned stb header, exercise channel counts 0–4 and vertical flipping, and compare memory/callback/file/filename loading at all three output precisions. They also cover allocation failures, short reads, metadata offsets, gamma and iPhone settings, animated-GIF delays/disposal, TLS, public exports, header reproducibility, static linkage and compile-time options. Lossless output from the C implementation is compared byte for byte with stb. C/C++ integer results must match exactly; floating-point results allow small math-library rounding differences (relative tolerance 2e-7, absolute tolerance 1e-9). JPEG comparisons check API results and C/C++ agreement; they do not assert equality with stb pixels.

The differential runner can additionally consume the pinned Wuffs test corpus:

```sh
python tests/differential.py build/libadapter.so build/libreference.so build/libadapter_cpp.so /path/to/wuffs/test/data
```

On Windows, use `build/Release/adapter.dll`, `reference.dll`, and `adapter_cpp.dll`. On macOS, the library suffix is `.dylib`.

For AddressSanitizer (and UBSan on GCC/Clang):

```sh
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=RelWithDebInfo -DSTB_WUFFS_ASAN=ON
cmake --build build-asan --config RelWithDebInfo --target sanitizer
ctest --test-dir build-asan -C RelWithDebInfo -R '^sanitizer$' --output-on-failure
```

Windows needs the compiler's AddressSanitizer runtime DLL on `PATH`.

## Maintenance and deliberate fixes

Edit `src/wuffs_backend.h` and `src/wuffs_config.h`, then run:

```sh
python tools/amalgamate.py
python tools/amalgamate.py --check
```

The generator verifies the vendored hashes and applies explicit, checked transformations. Do not edit the generated header or pristine vendor files directly. In addition to the decoder integration, it:

- internalizes Wuffs initializer, allocation, status and vtable symbols for correct static linkage;
- fixes animated-GIF flipping with requested channels other than four and guards failed loads;
- restores the saved canvas for consecutive GIF disposal-3 frames and removes invalid previous-frame pointer arithmetic;
- releases the original pixel allocation when precision conversion runs out of memory and prevents flipping a null conversion result;
- initializes JPEG fallback pixel planes so truncated decodes do not expose uninitialized pixel data;
- enables the missing 16-bit conversion helpers in PNM-only builds;
- aggregates short callback reads and safely treats null/negative-length memory input as empty input.

These corrections intentionally do not reproduce the corresponding upstream defects. They are covered by targeted regression tests. The project is not an exhaustive fuzzing campaign, and passing its corpus is not proof of equivalence for every malformed image.

## License

Adapter additions are MIT licensed. stb and Wuffs retain their upstream licenses; the generated header includes the applicable MIT notices. See `LICENSE`, `vendor/WUFFS-LICENSE-MIT`, and `vendor/WUFFS-LICENSE-APACHE`. This project is not affiliated with Google or the stb authors.
