/* Private, statically linked Wuffs implementation. */
#if !defined(STBI_WUFFS_DISABLE)
#if defined(WUFFS_INCLUDE_GUARD) || defined(WUFFS_IMPLEMENTATION) || defined(WUFFS_CONFIG__MODULES)
#error "Compile stb-wuffs in a separate translation unit from other Wuffs implementations"
#endif
#define WUFFS_IMPLEMENTATION
#define WUFFS_CONFIG__STATIC_FUNCTIONS
#define WUFFS_CONFIG__MODULES
#define WUFFS_CONFIG__MODULE__BASE
#if defined(STBI_NO_SIMD) && !defined(WUFFS_CONFIG__AVOID_CPU_ARCH)
#define WUFFS_CONFIG__AVOID_CPU_ARCH
#define STBI__WUFFS_UNDEF_AVOID_CPU_ARCH
#endif
#ifndef STBI_NO_PNG
#define WUFFS_CONFIG__MODULE__PNG
#define WUFFS_CONFIG__MODULE__ADLER32
#define WUFFS_CONFIG__MODULE__CRC32
#define WUFFS_CONFIG__MODULE__DEFLATE
#define WUFFS_CONFIG__MODULE__ZLIB
#endif
#ifndef STBI_NO_BMP
#define WUFFS_CONFIG__MODULE__BMP
#endif
#ifndef STBI_NO_GIF
#define WUFFS_CONFIG__MODULE__GIF
#define WUFFS_CONFIG__MODULE__LZW
#endif
#ifndef STBI_NO_JPEG
#define WUFFS_CONFIG__MODULE__JPEG
#endif
#ifndef STBI_NO_PNM
#define WUFFS_CONFIG__MODULE__NETPBM
#endif
#ifndef STBI_NO_TGA
#define WUFFS_CONFIG__MODULE__TARGA
#endif
/* Upstream generated code has warnings outside the adapter's control. */
#ifdef _MSC_VER
#pragma warning(push, 0)
#endif
#if defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#endif
/* WUFFS_AMALGAMATION */
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#ifdef _MSC_VER
#pragma warning(pop)
#endif
#undef WUFFS_IMPLEMENTATION
#undef WUFFS_CONFIG__STATIC_FUNCTIONS
#undef WUFFS_CONFIG__MODULES
#undef WUFFS_CONFIG__MODULE__BASE
#undef WUFFS_CONFIG__MODULE__PNG
#undef WUFFS_CONFIG__MODULE__ADLER32
#undef WUFFS_CONFIG__MODULE__CRC32
#undef WUFFS_CONFIG__MODULE__DEFLATE
#undef WUFFS_CONFIG__MODULE__ZLIB
#undef WUFFS_CONFIG__MODULE__BMP
#undef WUFFS_CONFIG__MODULE__GIF
#undef WUFFS_CONFIG__MODULE__LZW
#undef WUFFS_CONFIG__MODULE__JPEG
#undef WUFFS_CONFIG__MODULE__NETPBM
#undef WUFFS_CONFIG__MODULE__TARGA
#ifdef STBI__WUFFS_UNDEF_AVOID_CPU_ARCH
#undef WUFFS_CONFIG__AVOID_CPU_ARCH
#undef STBI__WUFFS_UNDEF_AVOID_CPU_ARCH
#endif
#endif
