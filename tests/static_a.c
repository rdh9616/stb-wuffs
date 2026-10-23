#define STB_IMAGE_STATIC
#define STB_IMAGE_IMPLEMENTATION
#include "../stb_image.h"
int static_b(void);
int main(void)
{
   stbi_set_flip_vertically_on_load(0);
   return static_b();
}
