# Implementation status

6 October 2026

| Work | Result |
| --- | --- |
| Static metadata index | 92 images, 14,861 types, 102,219 methods, 60,329 fields |
| Native addresses | 96,723 mapped methods per architecture; 89 modules in ARM64 and x86_64 |
| Unmapped direct pointers | 5,496 methods per architecture; generics and abstract methods need further analysis |
| Scene inventory | 36 built scenes indexed |
| Initial recovery target | Whirling floor 2, build index 6; 1,617 objects, 998 built-in components exported |
| iPad host | UIKit touch harness; Unity and recovered gameplay pending |
| Verification | 9 Python tests and 4 Swift tests pass; device and simulator builds succeed |
| Launch check | Harness launched and layout inspected on the installed 13 inch iPad Pro M5 simulator; physical M4 execution pending |

Next: resolve shared assets and custom script layouts for scene 6, then test texture recovery and gameplay integration.
