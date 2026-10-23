/* Declarations may be included before enabling the implementation. */
#include "../stb_image.h"
#define STB_IMAGE_IMPLEMENTATION
#include "../stb_image.h"
int compile_probe(void)
{
   int x, y, n;
   const unsigned char invalid[] = {0, 1, 2, 3};
   void *p = stbi_load_from_memory(invalid, sizeof(invalid), &x, &y, &n, 4);
   stbi_image_free(p);
   return stbi_info_from_memory(invalid, sizeof(invalid), &x, &y, &n);
}
int main(void) { return compile_probe(); }
