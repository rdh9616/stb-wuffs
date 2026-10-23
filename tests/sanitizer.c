#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define STBI_MAX_DIMENSIONS 1024
#define STB_IMAGE_IMPLEMENTATION
#include "../stb_image.h"

static void exercise(const unsigned char *p, int n)
{
   int x, y, c, req;
   for (req = 0; req <= 4; ++req)
   {
      stbi_image_free(stbi_load_from_memory(p, n, &x, &y, &c, req));
      stbi_image_free(stbi_load_16_from_memory(p, n, &x, &y, &c, req));
      stbi_image_free(stbi_loadf_from_memory(p, n, &x, &y, &c, req));
   }
   stbi_info_from_memory(p, n, &x, &y, &c);
   stbi_is_hdr_from_memory(p, n);
   stbi_is_16_bit_from_memory(p, n);
   if (n >= 6 && memcmp(p, "GIF8", 4) == 0)
   {
      int z, *delays = NULL;
      for (req = 1; req <= 4; ++req)
      {
         stbi_image_free(stbi_load_gif_from_memory(p, n, &delays, &x, &y, &z, &c, req));
         stbi_image_free(delays);
         delays = NULL;
      }
   }
}

int main(int argc, char **argv)
{
   int i;
   unsigned char random_bytes[128];
   unsigned state = 123456789;
   stbi_set_flip_vertically_on_load(1);
   for (i = 1; i < argc; ++i)
   {
      FILE *f = fopen(argv[i], "rb");
      long n;
      unsigned char *p;
      if (!f)
         return 1;
      fseek(f, 0, SEEK_END);
      n = ftell(f);
      rewind(f);
      if (n < 0 || n > 4000000)
      {
         fclose(f);
         continue;
      }
      p = (unsigned char *)malloc((size_t)n + 1);
      if (!p || fread(p, 1, (size_t)n, f) != (size_t)n)
         return 2;
      fclose(f);
      exercise(p, (int)n);
      /* Truncated PNG/JPEG inputs exercise real decoder error paths. */
      if (n > 8 && ((p[0] == 137 && p[1] == 'P') || (p[0] == 255 && p[1] == 216)))
      {
         int j;
         for (j = 0; j < n; j += 13)
            exercise(p, j);
      }
      free(p);
   }
   for (i = 0; i < 1000; ++i)
   {
      int j;
      for (j = 0; j < 128; ++j)
      {
         state = state * 1664525u + 1013904223u;
         random_bytes[j] = (unsigned char)(state >> 24);
      }
      exercise(random_bytes, i % 128);
   }
   puts("PASS: sanitizer corpus, PNG/JPEG truncations and 1000 deterministic random inputs");
   return 0;
}
