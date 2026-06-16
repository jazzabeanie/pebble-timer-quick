#include "mnemonic.h"

// Mnemonic Major System peg words.
// Adjective encodes the hour (00–23); noun encodes the minute (00–59).
// Source: Wikipedia "Mnemonic major system" 2-digit peg table.

static const char *s_adjectives[24] = {
  "sissy",    // 00
  "sad",      // 01
  "snowy",    // 02
  "awesome",  // 03
  "sorry",    // 04
  "slow",     // 05
  "swishy",   // 06
  "sick",     // 07
  "savvy",    // 08
  "sappy",    // 09
  "dizzy",    // 10
  "tight",    // 11
  "wooden",   // 12
  "tame",     // 13
  "dry",      // 14
  "tall",     // 15
  "whitish",  // 16
  "thick",    // 17
  "deaf",     // 18
  "deep",     // 19
  "noisy",    // 20
  "neat",     // 21
  "neon",     // 22
  "numb",     // 23
};

static const char *s_nouns[60] = {
  "sauce",    // 00
  "seed",     // 01
  "sun",      // 02
  "sumo",     // 03
  "sierra",   // 04
  "soil",     // 05
  "sewage",   // 06
  "sky",      // 07
  "sofa",     // 08
  "soap",     // 09
  "daisy",    // 10
  "tattoo",   // 11
  "tuna",     // 12
  "dome",     // 13
  "diary",    // 14
  "tail",     // 15
  "dish",     // 16
  "dog",      // 17
  "dove",     // 18
  "tuba",     // 19
  "nose",     // 20
  "net",      // 21
  "onion",    // 22
  "enemy",    // 23
  "winery",   // 24
  "nail",     // 25
  "nacho",    // 26
  "neck",     // 27
  "knife",    // 28
  "honeybee", // 29
  "mouse",    // 30
  "meadow",   // 31
  "moon",     // 32
  "mummy",    // 33
  "emery",    // 34
  "mole",     // 35
  "match",    // 36
  "mug",      // 37
  "movie",    // 38
  "map",      // 39
  "rice",     // 40
  "road",     // 41
  "rain",     // 42
  "rum",      // 43
  "aurora",   // 44
  "railway",  // 45
  "roach",    // 46
  "rag",      // 47
  "roof",     // 48
  "rope",     // 49
  "louse",    // 50
  "lady",     // 51
  "lion",     // 52
  "lime",     // 53
  "lorry",    // 54
  "lily",     // 55
  "leech",    // 56
  "leg",      // 57
  "lava",     // 58
  "lip",      // 59
};

void mnemonic_generate_name(int hour, int minute,
                             const char **adj_out, const char **noun_out) {
  *adj_out  = s_adjectives[hour];
  *noun_out = s_nouns[minute];
}
