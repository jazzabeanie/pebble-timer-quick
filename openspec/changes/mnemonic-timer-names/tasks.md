## 1. Mnemonic Lookup Tables

- [ ] 1.1 Create `src/mnemonic.h` with public API: `void mnemonic_generate_name(int hour, int minute, const char **adj_out, const char **noun_out)`
- [ ] 1.2 Create `src/mnemonic.c` with `static const char *s_adjectives[24]` (hours 00–23) and `static const char *s_nouns[60]` (minutes 00–59) using the Wikipedia Mnemonic Major System 2-digit peg words
- [ ] 1.3 Implement `mnemonic_generate_name()` to index both arrays and write pointers to `adj_out` and `noun_out`

## 2. Timer Struct and Persist

- [ ] 2.1 Add `char name[20]` field to the `Timer` struct in `src/timer.h`
- [ ] 2.2 Increment `PERSIST_VERSION` in `src/timer.c` to invalidate old saves

## 3. Name Assignment at Creation

- [ ] 3.1 Add a static helper `prv_assign_name(uint8_t new_idx)` in `src/timer.c` that extracts local HH:MM from `timer_slots[new_idx].start_ms`, calls `mnemonic_generate_name()`, builds the base name string, and loops with suffix " 2", " 3", etc. until the name is unique among existing slots
- [ ] 3.2 Call `prv_assign_name()` at the end of `timer_slot_create()` before returning

## 4. Timer List Display

- [ ] 4.1 In `src/timer_list.c`, replace the `line1` computation for existing timer entries (both the chrono and countdown branches, lines ~154–161) with `strncpy(line1, timer_slots[slot].name, sizeof(line1) - 1)` followed by a NUL terminator

## 5. Tests

- [ ] 5.1 Write a unit test (or functional test) that verifies `mnemonic_generate_name(14, 30, ...)` returns `"dry"` and `"mouse"`
- [ ] 5.2 Write a test that creates a timer at a known time and confirms `timer_slots[idx].name` equals the expected adjective-noun string
- [ ] 5.3 Write a test that creates two timers at the same minute and confirms the second receives the " 2" suffix
- [ ] 5.4 Write a test that creates three timers at the same minute and confirms the third receives the " 3" suffix
- [ ] 5.5 Write a functional test that opens the Timer List and verifies line 1 of an existing timer entry shows the timer's mnemonic name (not a duration string)
- [ ] 5.6 Write a test that confirms that editing an existing stopwatch doesn't change the name.
