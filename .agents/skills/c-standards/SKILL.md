---
name: c-standards
description: Strict mission-critical C coding standards for real-time embedded systems (BARR-C:2018, NASA JPL Power of Ten, MISRA C:2023, AUTOSAR).
---

# EMBEDDED C STRICT CODING STANDARD (ANTIGRAVITY DIRECTIVE)

## 1. CORE MANDATES
1. MEMORY MANAGEMENT:
   - Dynamic memory allocation functions (`malloc`, `calloc`, `realloc`, `free`, `sbrk`, `alloca`) are STRICTLY BANNED after system initialization.
   - All data structures, thread stacks, and communication buffers MUST be statically allocated at compile-time or initialized on stack within provable bounds.

2. TYPES & NUMERICAL INTEGRITY:
   - Built-in types `short`, `long`, and plain `char` are BANNED (except `char` for text string literals).
   - Use ONLY explicit fixed-width types from `<stdint.h>` (`uint8_t`, `int16_t`, `uint32_t`, `int32_t`, `uint64_t`, `int64_t`) and `<stdbool.h>`.
   - Floating-point calculations MUST use `float` or `double` explicitly. All numeric constants MUST include type suffixes (e.g., `100u`, `0.05f`).

3. CONTROL FLOW & DETERMINISM:
   - Recursion (direct or indirect) is STRICTLY BANNED to guarantee a static, bounded call stack depth (DAG).
   - Unconditional jumps (`goto`, `setjmp`, `longjmp`) are STRICTLY BANNED.
   - All loops (`for`, `while`) MUST have provable, static upper iteration bounds. Non-terminating server loops must be explicitly annotated with `/* @non-terminating@ */`.

4. DEFENSIVE PROGRAMMING & ASSERTIONS:
   - Validate ALL input parameters of public functions (`NULL` pointer checks, numeric range checks) before processing.
   - Check and handle the return values of ALL non-void functions.
   - Use non-side-effect assertions (`c_assert`) to enforce invariants during debug builds.

5. POINTERS, SCOPE & VISIBILITY:
   - Maximum pointer indirection level is 1 (`T *ptr`). Double pointers (`T **ptr`) and function pointers are prohibited unless explicitly approved for OS abstraction layers.
   - Minimize variable scope. Declare variables at the point of first use.
   - Functions and variables not referenced outside their compilation unit MUST be declared `static` (internal linkage).
   - Use `const` for all read-only parameters, pointers, and lookup tables.

6. CONCURRENCY & THREAD SAFETY:
   - All shared state between threads MUST be protected by `pthread_mutex_t`.
   - Mutexes MUST be initialized with priority inheritance protocol (`PTHREAD_PRIO_INHERIT`) to prevent priority inversion.
   - Direct access to global variables is BANNED; access MUST be mediated via thread-safe getter/setter functions.

7. REAL-TIME TEMPORIZATION:
   - Periodic loops MUST use `clock_nanosleep` with `CLOCK_MONOTONIC` and `TIMER_ABSTIME` to eliminate execution temporal drift.
   - Non-monotonic clocks (`CLOCK_REALTIME`, `sleep`, `usleep`) are BANNED for periodic task timing.

---

## 2. CODE STYLE AND NAMING CONVENTIONS (BARR-C:2018)
- Naming Case: Use `snake_case` for functions, variables, and structure members.
- Type Definitions: All `typedef` names MUST end with the suffix `_t` (e.g., `shared_buffer_t`).
- Pointer Variables: Prefix pointer variable names with `p_` (e.g., `p_shared_data`).
- Global Variables: Prefix global/module-static variables with `g_` (e.g., `g_telemetry_mutex`).
- Constants & Macros: Use `UPPER_SNAKE_CASE` for `#define` macros and `enum` constants.
- Line Width: Hard limit of 80 characters per line.

---

## 3. COMPILER STRICTNESS & FLAGS
All C code MUST compile cleanly with ZERO warnings under `gcc` / `clang` using the following compilation flags:
```flags
-Wall -Wextra -Werror -pedantic -std=c99 -pthread
