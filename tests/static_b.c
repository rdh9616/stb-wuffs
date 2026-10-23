#define STB_IMAGE_STATIC
#define STB_IMAGE_IMPLEMENTATION
#include "../stb_image.h"
int static_b(void)
{
   stbi_image_free(NULL);
   return 0;
}
