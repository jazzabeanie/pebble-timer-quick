# Button Press Comparison: QuickTimer vs Default Pebble Timer

Button presses required to set a countdown timer, including 1 press to open the app.

QuickTimer buttons in New mode: Up (+20 min), Select (+5 min), Down (+1 min), Back (+60 min). Long-press Up toggles reverse direction (all increments become decrements).

```
| Timer Amount | QuickTimer | Method                                   | Default Pebble Timer |
|--------------|------------|------------------------------------------|----------------------|
| 1 min        | 2          | Down                                     |  5                   |
| 2 min        | 3          | Down x2                                  |  6                   |
| 3 min        | 4          | Down x3                                  |  7                   |
| 4 min        | 4          | Select, reverse, Down                    |  8                   |
| 5 min        | 2          | Select                                   |  5+                  |
| 6 min        | 3          | Select, Down                             |  5+                  |
| 7 min        | 4          | Select, Down x2                          |  5+                  |
| 8 min        | 5          | Select, Down x3                          |  5+                  |
| 9 min        | 5          | Select x2, reverse, Down                 |  5+                  |
| 10 min       | 3          | Select x2                                |  5+                  |
| 11 min       | 4          | Select x2, Down                          |  5+                  |
| 12 min       | 5          | Select x2, Down x2                       |  5+                  |
| 13 min       | 6          | Select x2, Down x3                       |  5+                  |
| 14 min       | 5          | Up, reverse, Select, Down                |  5+                  |
| 15 min       | 4          | Select x3                                |  5+                  |
| 16 min       | 5          | Select x3, Down                          |  5+                  |
| 17 min       | 6          | Select x3, Down x2                       |  5+                  |
| 18 min       | 5          | Up, reverse, Down x2                     |  5+                  |
| 19 min       | 4          | Up, reverse, Down                        |  5+                  |
| 20 min       | 2          | Up                                       |  5+                  |
| 25 min       | 3          | Up, Select                               |  5+                  |
| 30 min       | 4          | Up, Select x2                            |  5+                  |
| 35 min       | 5          | Up, Select x3                            |  5+                  |
| 40 min       | 3          | Up x2                                    |  5+                  |
| 45 min       | 4          | Up x2, Select                            |  5+                  |
| 50 min       | 5          | Up x2, Select x2                         |  5+                  |
| 55 min       | 4          | Back, reverse, Select                    |  5+                  |
| 59 min       | 4          | Back, reverse, Down                      |  5                   |
| 60 min       | 2          | Back                                     |  5                   |
```
