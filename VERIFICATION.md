# Verification record

Test date: 2026-10-23. Dependency versions and hashes: `vendor/manifest.json`.

Local platform: Windows x64, MSVC 19.39.33523.0, CMake 3.29.2, Python 3.12.3.

- C and C++ implementations built successfully.
- The 43 standard public functions were found in the shared-library exports; the optional Windows UTF-8 API is included in the configuration build matrix.
- The generated fixture suite passed 4,866 comparisons across 46 image files, covering all nine stb image format families, all requested channel counts, all three output precisions, flipping and the four input routes. Lossless C pixels are compared exactly with stb; C/C++ floats allow small math-library rounding differences. JPEG pixels are not compared for equality with stb. Packed 16-bit RGB TGA and partial first-frame GIF backgrounds have explicit compatibility regressions.
- The pinned Wuffs upstream corpus passed 13,686 comparisons across 131 image files, including interlaced PNGs, BMP variants, GIFs, baseline/progressive/subsampled JPEGs and truncated files. Only files up to 3,000,000 compressed bytes were selected. Full arbitrary-corpus equivalence is not established.
- 1,440 injected allocation-failure cases passed with zero outstanding allocations, covering memory/callback inputs and all three output precisions.
- Targeted checks passed for GIF delays, reduced-channel flipping, consecutive disposal-3 frames against Pillow-rendered expected frames, tiny callback reads, PNG truncation compatibility, file-probe offset preservation, gamma/iPhone options, zlib functions and thread-local flipping.
- Twenty-two configuration executables and a two-translation-unit static-link executable built and ran successfully. The configuration set is recorded in `CMakeLists.txt`; it is not every possible combination of macros.
- Header generation is deterministic and verifies pristine vendor SHA-256 hashes.
- Local MSVC AddressSanitizer initially stopped before `main` with an interception-runtime failure, both sandboxed and outside the sandbox. With the runtime's `ASAN_WIN_CONTINUE_ON_INTERCEPTION_FAILURE=1` setting, the fixture/truncation harness and 1,000 deterministic random inputs passed. This is a limited local sanitizer result because interception coverage was reduced. The committed Linux CI sanitizer job runs AddressSanitizer, leak checking and UBSan without that workaround.

Cross-platform CI results are available in the repository's Actions tab after publication. They must not be inferred from the local Windows result. No performance benchmark or exhaustive fuzzing result is claimed.
