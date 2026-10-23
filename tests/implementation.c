#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
static int test_hits[7];
static int test_allocations;
static int test_fail_after = -1;
static void *test_malloc(size_t n)
{
   void *p;
   if (test_fail_after == 0)
      return NULL;
   if (test_fail_after > 0)
      --test_fail_after;
   p = malloc(n);
   if (p)
      ++test_allocations;
   return p;
}
static void test_free(void *p)
{
   if (p)
      --test_allocations;
   free(p);
}
static void *test_realloc(void *p, size_t n)
{
   void *q;
   int had_pointer = p != NULL;
   if (test_fail_after == 0)
      return NULL;
   if (test_fail_after > 0)
      --test_fail_after;
   q = realloc(p, n);
   if (q && !had_pointer)
      ++test_allocations;
   return q;
}
#define STBI_MALLOC test_malloc
#define STBI_REALLOC test_realloc
#define STBI_FREE test_free
#define STBI_WUFFS_ON_DECODE(format) (++test_hits[format])
#define STB_IMAGE_IMPLEMENTATION
#ifdef TEST_REFERENCE
#include "../vendor/stb_image.h"
#else
#include "../stb_image.h"
#endif

#ifdef __cplusplus
extern "C"
{
#endif
   int test_native_hits(int kind) { return test_hits[kind]; }
   int test_live_allocations(void) { return test_allocations; }
   void test_fail_allocation(int after) { test_fail_after = after; }
   /* Keep FILE* inside its own C runtime when called by Python. */
   unsigned char *test_file(const char *path, int *x, int *y, int *c, int req, long *pos, int mode)
   {
      FILE *f = fopen(path, "rb");
      void *p = NULL;
      if (!f)
         return NULL;
      if (mode == 0)
         p = stbi_load_from_file(f, x, y, c, req);
      if (mode == 1)
         p = stbi_load_from_file_16(f, x, y, c, req);
      if (mode == 2)
         p = stbi_loadf_from_file(f, x, y, c, req);
      if (mode == 3)
      {
         stbi_info_from_file(f, x, y, c);
      }
      if (mode == 4)
      {
         *c = stbi_is_16_bit_from_file(f);
      }
      if (mode == 5)
      {
         *c = stbi_is_hdr_from_file(f);
      }
      *pos = ftell(f);
      fclose(f);
      return (unsigned char *)p;
   }
#ifdef __cplusplus
}
#endif
