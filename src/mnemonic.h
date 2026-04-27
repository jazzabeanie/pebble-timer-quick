#pragma once

// Returns pointers into static arrays — do not free.
void mnemonic_generate_name(int hour, int minute,
                             const char **adj_out, const char **noun_out);
