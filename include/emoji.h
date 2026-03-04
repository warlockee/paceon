/*
 * emoji.h - Emoji parsing for paceon
 *
 * Calling spec:
 *   Pure functions. Match emoji byte sequences. No side effects.
 *   - match_red_heart(p, remaining) -> int (bytes consumed or 0)
 *   - match_colored_heart(p, remaining, heart) -> int
 *   - match_orange_heart(p, remaining) -> int
 *   - match_purple_heart(p, remaining) -> int
 *   - ends_with_purple_heart(text) -> int (1=yes)
 */

#ifndef PACEON_EMOJI_H
#define PACEON_EMOJI_H

#include <stddef.h>

int match_red_heart(const unsigned char *p, size_t remaining);
int match_colored_heart(const unsigned char *p, size_t remaining, char *heart);
int match_orange_heart(const unsigned char *p, size_t remaining);
int match_purple_heart(const unsigned char *p, size_t remaining);
int ends_with_purple_heart(const char *text);

#endif /* PACEON_EMOJI_H */
