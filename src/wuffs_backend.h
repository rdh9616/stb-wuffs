/* MIT licensed adapter glue. Upstream stb supplies the public API and fallbacks. */
#ifndef STBI_WUFFS_ON_DECODE
#define STBI_WUFFS_ON_DECODE(format) ((void)(format))
#endif

#if !defined(STBI_WUFFS_DISABLE)
#if defined(STBI_NO_PNG) && defined(STBI_NO_BMP) && defined(STBI_NO_GIF) &&                        \
    defined(STBI_NO_JPEG) && defined(STBI_NO_PNM) && defined(STBI_NO_TGA)
#define STBI__WUFFS_NO_NATIVE
#endif
#endif

#if !defined(STBI_WUFFS_DISABLE) && !defined(STBI__WUFFS_NO_NATIVE)
typedef struct
{
   stbi__context *original;
   const stbi_uc *data;
   stbi_uc *owned;
   size_t length, capacity, position;
   int closed;
} stbi__wuffs_input;

/* Keep bytes already read so a decoder rejection can be replayed without
   requiring the input to be seekable. Only unused lookahead is ungot on success,
   using the negative-skip operation specified by stbi_io_callbacks. */
static int stbi__wuffs_fill(stbi__wuffs_input *in, wuffs_base__io_buffer *src)
{
   size_t capacity;
   stbi_uc *p;
   int n;
   if (in->closed || !in->original->io.read)
      return 0;
   if (in->capacity - in->length < 4096)
   {
      if (in->capacity >= INT_MAX)
         return 0;
      capacity = in->capacity < 4096 ? 4096 : in->capacity * 2;
      if (capacity > INT_MAX)
         capacity = INT_MAX;
      p = (stbi_uc *)STBI_REALLOC_SIZED(in->owned, in->capacity, capacity);
      if (!p)
         return 0;
      in->owned = p;
      in->data = p;
      in->capacity = capacity;
   }
   n = (int)(in->capacity - in->length);
   if (n > 4096)
      n = 4096;
   n = in->original->io.read(in->original->io_user_data, (char *)in->owned + in->length, n);
   if (n <= 0)
   {
      in->closed = 1;
      n = 0;
   }
   in->length += (size_t)n;
   src->data = wuffs_base__make_slice_u8(in->owned, in->length);
   src->meta.wi = in->length;
   src->meta.closed = in->closed != 0;
   return n != 0;
}

static int stbi__wuffs_replay_read(void *user, char *data, int size)
{
   stbi__wuffs_input *in = (stbi__wuffs_input *)user;
   size_t n = in->length - in->position;
   int extra = 0;
   if (n > (size_t)size)
      n = (size_t)size;
   if (n)
      memcpy(data, in->data + in->position, n);
   in->position += n;
   if ((int)n < size && !in->closed)
   {
      extra = in->original->io.read(in->original->io_user_data, data + n, size - (int)n);
      if (extra <= 0)
      {
         extra = 0;
         in->closed = 1;
      }
   }
   return (int)n + extra;
}

static void stbi__wuffs_replay_skip(void *user, int n)
{
   stbi__wuffs_input *in = (stbi__wuffs_input *)user;
   size_t available = in->length - in->position;
   if (n >= 0)
   {
      size_t take = (size_t)n < available ? (size_t)n : available;
      in->position += take;
      n -= (int)take;
   }
   if (n)
      in->original->io.skip(in->original->io_user_data, n);
}

static int stbi__wuffs_replay_eof(void *user)
{
   stbi__wuffs_input *in = (stbi__wuffs_input *)user;
   return in->position == in->length &&
          (in->closed || in->original->io.eof(in->original->io_user_data));
}

static void stbi__wuffs_unget(stbi__context *s, size_t n)
{
   while (n)
   {
      int k = n > INT_MAX ? INT_MAX : (int)n;
      s->io.skip(s->io_user_data, -k);
      n -= (size_t)k;
   }
   /* stbi_load_from_file must not unget these same bytes a second time. */
   s->img_buffer = s->img_buffer_end = s->buffer_start;
}

static wuffs_base__image_decoder *stbi__wuffs_decoder(int kind)
{
   /* Do not use Wuffs' malloc-based alloc helpers: honor STBI_MALLOC/FREE. */
#define STBI__WUFFS_MAKE(tag)                                                                      \
   do                                                                                              \
   {                                                                                               \
      wuffs_##tag##__decoder *d =                                                                  \
          (wuffs_##tag##__decoder *)STBI_MALLOC(sizeof__wuffs_##tag##__decoder());                 \
      if (!d)                                                                                      \
         return NULL;                                                                              \
      if (wuffs_##tag##__decoder__initialize(d, sizeof__wuffs_##tag##__decoder(), WUFFS_VERSION,   \
                                             0)                                                    \
              .repr)                                                                               \
      {                                                                                            \
         STBI_FREE(d);                                                                             \
         return NULL;                                                                              \
      }                                                                                            \
      return wuffs_##tag##__decoder__upcast_as__wuffs_base__image_decoder(d);                      \
   } while (0)
   switch (kind)
   {
#ifndef STBI_NO_PNG
   case 1:
      STBI__WUFFS_MAKE(png);
#endif
#ifndef STBI_NO_BMP
   case 2:
      STBI__WUFFS_MAKE(bmp);
#endif
#ifndef STBI_NO_GIF
   case 3:
      STBI__WUFFS_MAKE(gif);
#endif
#ifndef STBI_NO_JPEG
   case 4:
      STBI__WUFFS_MAKE(jpeg);
#endif
#ifndef STBI_NO_PNM
   case 5:
      STBI__WUFFS_MAKE(netpbm);
#endif
#ifndef STBI_NO_TGA
   case 6:
      STBI__WUFFS_MAKE(targa);
#endif
   default:
      return NULL;
   }
#undef STBI__WUFFS_MAKE
}

static int stbi__wuffs_kind(stbi__context *s)
{
#ifndef STBI_NO_PNG
   if (stbi__png_test(s))
      return 1;
#endif
#ifndef STBI_NO_BMP
   if (stbi__bmp_test(s))
      return 2;
#endif
#ifndef STBI_NO_GIF
   if (stbi__gif_test(s))
      return 3;
#endif
#if !defined(STBI_NO_JPEG) && !defined(STBI_WUFFS_EXACT_JPEG)
   if (stbi__jpeg_test(s))
      return 4;
#endif
#ifndef STBI_NO_PNM
   if (stbi__pnm_test(s))
      return 5;
#endif
#ifndef STBI_NO_TGA
   if (stbi__tga_test(s))
      return 6;
#endif
   STBI_NOTUSED(s);
   return 0;
}

/* Wuffs accepts a GIF LZW stream without an initial clear code; stb rejects it.
   Check only this structural distinction, leaving actual LZW decoding to Wuffs. */
static int stbi__wuffs_gif_initial_clear(const stbi_uc *p, size_t n)
{
   size_t i = 13;
   if (n < i)
      return 0;
   if (p[10] & 128)
      i += (size_t)3 << ((p[10] & 7) + 1);
   while (i < n)
   {
      if (p[i] == 0x21)
      {
         i += 2;
         while (i < n && p[i])
         {
            size_t len = p[i++];
            if (len > n - i)
               return 0;
            i += len;
         }
         if (i >= n)
            return 0;
         ++i;
      }
      else if (p[i] == 0x2C)
      {
         unsigned bits, value = 0, count = 0;
         if (n - i < 10)
            return 0;
         if (p[i + 9] & 128)
         {
            size_t palette = (size_t)3 << ((p[i + 9] & 7) + 1);
            if (palette > n - i - 10)
               return 0;
            i += palette;
         }
         i += 10;
         if (i >= n)
            return 0;
         bits = p[i++];
         if (bits > 8)
            return 0;
         while (i < n)
         {
            size_t len = p[i++], j;
            if (!len)
               return 1;
            if (len > n - i)
               return 0;
            for (j = 0; j < len && count <= bits; ++j)
            {
               value |= (unsigned)p[i + j] << count;
               count += 8;
            }
            if (count > bits)
            {
               value &= (1u << (bits + 1)) - 1;
               return value == (1u << bits) || value == (1u << bits) + 1;
            }
            i += len;
         }
         return 0;
      }
      else
      {
         return 0;
      }
   }
   return 0;
}

/* Keep conversion available in STBI_ONLY_JPEG builds too. */
static stbi_uc *stbi__wuffs_convert(stbi_uc *src, int from, int to, int w, int h)
{
   size_t i, count = (size_t)w * (size_t)h;
   stbi_uc *dst;
   if (from == to)
      return src;
   if (!stbi__mad3sizes_valid(w, h, to, 0))
   {
      STBI_FREE(src);
      return NULL;
   }
   dst = (stbi_uc *)STBI_MALLOC(count * (size_t)to);
   if (!dst)
   {
      STBI_FREE(src);
      return NULL;
   }
   for (i = 0; i < count; ++i)
   {
      const stbi_uc *p = src + i * (size_t)from;
      stbi_uc *q = dst + i * (size_t)to;
      stbi_uc r = p[0], g = from == 1 ? r : p[1], b = from == 1 ? r : p[2];
      stbi_uc a = from == 1 ? 255 : p[3];
      if (to <= 2)
      {
         q[0] = (stbi_uc)(((int)r * 77 + (int)g * 150 + (int)b * 29) >> 8);
         if (to == 2)
            q[1] = a;
      }
      else
      {
         q[0] = r;
         q[1] = g;
         q[2] = b;
         if (to == 4)
            q[3] = a;
      }
   }
   STBI_FREE(src);
   return dst;
}

/* stb consumes PNG through IEND, while Wuffs may finish at the end of IDAT.
   Walk the length-delimited container, without interpreting chunk payloads. */
static int stbi__wuffs_png_end(stbi__wuffs_input *in, wuffs_base__io_buffer *src, size_t *end)
{
   size_t pos = 8;
   for (;;)
   {
      stbi__uint32 len;
      while (in->length - pos < 8)
         if (!stbi__wuffs_fill(in, src))
            return 0;
      len = ((stbi__uint32)in->data[pos] << 24) | ((stbi__uint32)in->data[pos + 1] << 16) |
            ((stbi__uint32)in->data[pos + 2] << 8) | in->data[pos + 3];
      if (len > (stbi__uint32)INT_MAX - 12 || pos > (size_t)INT_MAX - len - 12)
         return 0;
      /* APNG's default image can differ from its first animation frame. */
      if (memcmp(in->data + pos + 4, "acTL", 4) == 0)
         return 0;
      /* Preserve RGB hidden under a transparent color-key (stb semantics). */
      if (memcmp(in->data + pos + 4, "tRNS", 4) == 0 && in->data[25] != 3)
         return 0;
      while (in->length - pos < (size_t)len + 12)
         if (!stbi__wuffs_fill(in, src))
            return 0;
      if (memcmp(in->data + pos + 4, "IEND", 4) == 0)
      {
         *end = pos + (size_t)len + 12;
         return 1;
      }
      pos += (size_t)len + 12;
   }
}

static stbi_uc *stbi__wuffs_try(stbi__wuffs_input *in, int kind, int *x, int *y, int *comp,
                                int req_comp, size_t *consumed)
{
   wuffs_base__image_decoder *dec = stbi__wuffs_decoder(kind);
   wuffs_base__io_buffer src =
       wuffs_base__ptr_u8__reader((uint8_t *)in->data, in->length, in->closed != 0);
   wuffs_base__image_config ic = wuffs_base__null_image_config();
   wuffs_base__pixel_config pc = wuffs_base__null_pixel_config();
   wuffs_base__pixel_buffer pb = wuffs_base__null_pixel_buffer();
   wuffs_base__status status;
   wuffs_base__range_ii_u64 range;
   wuffs_base__slice_u8 work = wuffs_base__empty_slice_u8();
   stbi_uc *pixels = NULL;
   int width = 0, height = 0, channels = 0, dst_channels, output_channels;
   size_t size;
   if (!dec)
      return NULL;
   wuffs_base__image_decoder__set_quirk(dec, WUFFS_BASE__QUIRK_IGNORE_CHECKSUM, 1);
   for (;;)
   {
      status = wuffs_base__image_decoder__decode_image_config(dec, &ic, &src);
      if (!status.repr)
         break;
      if (status.repr != wuffs_base__suspension__short_read || !stbi__wuffs_fill(in, &src))
         goto fail;
   }
   /* Preserve stb's source channel count and its full precision paths. */
   if (in->length > INT_MAX ||
       !stbi_info_from_memory(in->data, (int)in->length, &width, &height, &channels) ||
       stbi_is_16_bit_from_memory(in->data, (int)in->length))
      goto fail;
   /* BMP's unused fourth byte is treated as alpha by stb, but not Wuffs. */
   if (kind == 2 && channels == 4)
      goto fail;
   if (width <= 0 || height <= 0 || width > STBI_MAX_DIMENSIONS || height > STBI_MAX_DIMENSIONS ||
       (uint32_t)width != wuffs_base__pixel_config__width(&ic.pixcfg) ||
       (uint32_t)height != wuffs_base__pixel_config__height(&ic.pixcfg))
      goto fail;
   output_channels = req_comp ? req_comp : channels;
   /* JPEG's grey output is its Y channel, not luma of already-converted RGB. */
   dst_channels = (kind == 4 && output_channels <= 2) ? 1 : 4;
   if (!stbi__mad3sizes_valid(width, height, dst_channels, 0))
      goto fail;
   size = (size_t)width * (size_t)height * (size_t)dst_channels;
   pixels = (stbi_uc *)STBI_MALLOC(size);
   if (!pixels)
      goto fail;
   memset(pixels, 0, size);
   range = wuffs_base__image_decoder__workbuf_len(dec);
   if (wuffs_base__range_ii_u64__is_empty(&range) || range.max_incl > SIZE_MAX)
      goto fail;
   if (range.max_incl)
   {
      work.ptr = (uint8_t *)STBI_MALLOC((size_t)range.max_incl);
      if (!work.ptr)
         goto fail;
      work.len = (size_t)range.max_incl;
   }
   wuffs_base__pixel_config__set(
       &pc,
       dst_channels == 1 ? WUFFS_BASE__PIXEL_FORMAT__Y : WUFFS_BASE__PIXEL_FORMAT__RGBA_NONPREMUL,
       WUFFS_BASE__PIXEL_SUBSAMPLING__NONE, (uint32_t)width, (uint32_t)height);
   status =
       wuffs_base__pixel_buffer__set_from_slice(&pb, &pc, wuffs_base__make_slice_u8(pixels, size));
   if (status.repr)
      goto fail;
   for (;;)
   {
      status = wuffs_base__image_decoder__decode_frame(dec, &pb, &src, WUFFS_BASE__PIXEL_BLEND__SRC,
                                                       work, NULL);
      if (!status.repr)
         break;
      if (status.repr != wuffs_base__suspension__short_read || !stbi__wuffs_fill(in, &src))
         goto fail;
   }
   *consumed = src.meta.ri;
   if (kind == 1 && !stbi__wuffs_png_end(in, &src, consumed))
      goto fail;
   if (kind == 3 && !stbi__wuffs_gif_initial_clear(in->data, in->length))
      goto fail;
   STBI_FREE(work.ptr);
   STBI_FREE(dec);
   pixels = stbi__wuffs_convert(pixels, dst_channels, output_channels, width, height);
   if (pixels)
   {
      *x = width;
      *y = height;
      if (comp)
         *comp = channels;
      STBI_WUFFS_ON_DECODE(kind);
   }
   return pixels;
fail:
   STBI_FREE(pixels);
   STBI_FREE(work.ptr);
   STBI_FREE(dec);
   return NULL;
}
#endif

static void *stbi__load_main(stbi__context *s, int *x, int *y, int *comp, int req_comp,
                             stbi__result_info *ri, int bpc)
{
#if !defined(STBI_WUFFS_DISABLE) && !defined(STBI__WUFFS_NO_NATIVE)
   int kind;
   stbi__wuffs_input in;
   stbi_uc *pixels;
   size_t consumed = 0;
   if (req_comp < 0 || req_comp > 4)
      return stbi__errpuc("bad req_comp", "Invalid requested channel count");
   kind = stbi__wuffs_kind(s);
   stbi__rewind(s); /* stbi__pnm_test leaves its successful signature consumed. */
   if (!kind)
      return stbi__wuffs_fallback(s, x, y, comp, req_comp, ri, bpc);
   memset(&in, 0, sizeof(in));
   in.original = s;
   in.length = (size_t)(s->img_buffer_end - s->img_buffer);
   in.data = s->img_buffer;
   in.closed = s->io.read == NULL;
   if (!in.closed)
   {
      in.capacity = in.length ? in.length : 1;
      in.owned = (stbi_uc *)STBI_MALLOC(in.capacity);
      if (!in.owned)
         return stbi__wuffs_fallback(s, x, y, comp, req_comp, ri, bpc);
      if (in.length)
         memcpy(in.owned, in.data, in.length);
      in.data = in.owned;
   }
   pixels = stbi__wuffs_try(&in, kind, x, y, comp, req_comp, &consumed);
   if (pixels)
   {
      memset(ri, 0, sizeof(*ri));
      ri->bits_per_channel = 8;
      ri->channel_order = STBI_ORDER_RGB;
      if (s->io.read)
         stbi__wuffs_unget(s, in.length - consumed);
      else
         s->img_buffer += consumed;
   }
   else if (s->io.read)
   {
      stbi__context replay;
      stbi_io_callbacks cb = {stbi__wuffs_replay_read, stbi__wuffs_replay_skip,
                              stbi__wuffs_replay_eof};
      stbi__start_callbacks(&replay, &cb, &in);
      pixels = (stbi_uc *)stbi__wuffs_fallback(&replay, x, y, comp, req_comp, ri, bpc);
      if (pixels)
         stbi__wuffs_unget(s, in.length - in.position +
                                  (size_t)(replay.img_buffer_end - replay.img_buffer));
   }
   else
   {
      pixels = (stbi_uc *)stbi__wuffs_fallback(s, x, y, comp, req_comp, ri, bpc);
   }
   STBI_FREE(in.owned);
   return pixels;
#else
   return stbi__wuffs_fallback(s, x, y, comp, req_comp, ri, bpc);
#endif
}
