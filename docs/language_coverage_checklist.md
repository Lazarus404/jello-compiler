# Jello Language Coverage Checklist

This document describes the Jello language and maps each feature to test coverage. Use it as both a language reference and a checklist to ensure sufficient tests for a usable implementation.

---

## 1. Language Overview

Jello is a **statically typed**, **prototypal** language with **type inference** (Haxe-like ergonomics) and **ECMA-like syntax**. It targets a typed bytecode VM with explicit boxing at the `Dynamic` boundary.

- **Paradigm**: Functional bias; first-class functions and closures; prototypal objects with correct `this` binding
- **Source encoding**: UTF-8
- **Test convention**: Programs return `"ok"` on success; `System.assert(cond)` for checks; negative tests expect compile or runtime failure

---

## 2. Type System

### 2.1 Primitives

| Type                      | Description     | Tests                                                              |
| ------------------------- | --------------- | ------------------------------------------------------------------ |
| `i8`, `i16`, `i32`, `i64` | Signed integers | `numeric/small_type_arith.jello`, `numeric/literal_suffixes.jello` |
| `f16`, `f32`, `f64`       | Floats          | `numeric/div_float_implicit.jello`, `numeric/div_i32_f32.jello`    |
| `bool`                    | Boolean         | `bool/basic.jello`, `bool/eq_truthy.jello`, `bool/and_or.jello`    |
| `atom`                    | Symbol/atom     | `atom/literal_get.jello`                                           |

**Rules**: No implicit narrowing; widening allowed. Integer overflow wraps. Float→int is checked (trap on NaN/Inf/out-of-range).

### 2.2 Heap Types

| Type              | Description                   | Tests                                                               |
| ----------------- | ----------------------------- | ------------------------------------------------------------------- |
| `bytes`           | UTF-8 string (alias `string`) | `bytes/hello.jello`, `bytes/concat_many.jello`, `bytes/slice.jello` |
| `list<T>`         | Linked list                   | `match/list_head_tail.jello`                                        |
| `array<T>`        | Contiguous array              | `array/index_sugar.jello`, `array/bytes_ops.jello`                  |
| `object`          | Prototypal object             | `object/literal.jello`, `object/get.jello`, `object/assign.jello`   |
| `fun(...) -> ...` | Function type                 | `fn/infer_ackerman.jello`, `closure_call.jello`                     |
| `Any`             | Dynamic top type              | `object/dynamic_access.jello`                                       |

### 2.3 Inference

| Feature               | Description                | Tests                                                                   |
| --------------------- | -------------------------- | ----------------------------------------------------------------------- |
| Local inference       | Locals can be inferred     | `fn/infer_param_numeric_add.jello`, `fn/infer_param_bytes_concat.jello` |
| Param inference       | Params inferred from usage | `fn/infer_ackerman.jello`, `fn/infer_nested_fn_capture_and_param.jello` |
| Widening at call site | Arg widened to match param | `fn/infer_outer_typed_fun_call_widen_arg.jello`                         |

**Policy**: No global HM; bidirectional typing; inference at module boundaries is restricted.

---

## 3. Expressions

### 3.1 Literals

| Literal             | Form                         | Tests                                                                             |
| ------------------- | ---------------------------- | --------------------------------------------------------------------------------- |
| Integer             | `42`, `42i8`, `42i64`, etc.  | `numeric/literal_suffixes.jello`                                                  |
| Float               | `3.14`, `3.14f32`, `3.14f64` | `numeric/div_float_implicit.jello`                                                |
| Bool                | `true`, `false`              | `bool/basic.jello`                                                                |
| Bytes/string        | `'...'`, `"..."`             | `bytes/hello.jello`                                                               |
| Interpolated string | `` `... ${expr} ...` ``      | `bytes/interp_basic.jello`, `bytes/interp_many.jello`, `bytes/interp_order.jello` |
| Atom                | `#atom`                      | `atom/literal_get.jello`                                                          |
| Object              | `{a: 1, b: "hi"}`            | `object/literal.jello`                                                            |
| Tuple               | `(a, b)`                     | `tuple/basic.jello`, `tuple/eq.jello`                                             |

### 3.2 Operators

| Category     | Operators           | Rules                                        | Tests                                                                                         |
| ------------ | ------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Arithmetic   | `+ - * /` unary `-` | Numeric promotion; no implicit narrowing     | `numeric/arith_interchangeable.jello`, `numeric/mod_basic.jello`, `numeric/shift_basic.jello` |
| Comparison   | `== != < <= > >=`   | Value-based for numerics; cross-type allowed | `numeric/chained_eq_numeric.jello`, `i32/relops.jello`, `i32/lt.jello`                        |
| Logical      | `&& \|\|`           | Short-circuit                                | `bool/shortcircuit_minimal.jello`, `bool/shortcircuit_trap.jello`                             |
| Bytes concat | `+`                 | `bytes + bytes -> bytes` only                | `bytes/hello.jello`, `bytes/concat_many.jello`                                                |

### 3.3 String Escapes

| Escape                                             | Description    | Tests                        |
| -------------------------------------------------- | -------------- | ---------------------------- |
| `\\`, `\'`, `\"`, `` \` ``, `\n`, `\r`, `\t`, `\0` | Basic          | `bytes/hello.jello`          |
| `\uXXXX`                                           | 4 hex digits   | `bytes/unicode_escape.jello` |
| `\u{X...}`                                         | 1–6 hex digits | `bytes/unicode_escape.jello` |

**Validity**: Reject surrogates `U+D800..U+DFFF` and `> U+10FFFF`.

---

## 4. Control Flow

### 4.1 Conditionals

| Construct     | Syntax                           | Tests                                                |
| ------------- | -------------------------------- | ---------------------------------------------------- |
| `if/else`     | `if (cond) { ... } else { ... }` | `if/basic.jello`, `if/join.jello`                    |
| Ternary       | `cond ? a : b` (desugared to if) | (via `if/`)                                          |
| Short-circuit | `&&`, `\|\|`                     | `bool/shortcircuit_*.jello`, `bool/let_if_and.jello` |

### 4.2 Loops

| Construct            | Syntax                    | Tests                                                                 |
| -------------------- | ------------------------- | --------------------------------------------------------------------- |
| `while`              | `while (cond) { ... }`    | `while/countdown.jello`                                               |
| `do..while`          | `do { ... } while (cond)` | `while/do_while.jello`, `while/do_while_break_continue.jello` (break) |
| `break` / `continue` | Target nearest loop       | `while/break_continue.jello`                                          |

### 4.3 Match

| Feature           | Description                  | Tests                                                                  |
| ----------------- | ---------------------------- | ---------------------------------------------------------------------- |
| Scalar arms       | `1 => {...}`, `2 => {...}`   | `match/basic.jello`                                                    |
| Wildcard          | `_ => {...}` (required last) | `match/basic.jello`                                                    |
| Bind              | `x => {...}` binds subject   | —                                                                      |
| Pin               | `^x` matches existing var    | `match/object_pin.jello`                                               |
| Object            | `{a: p, b: p}`               | `match/object_wildcard.jello`, `match/object_own_only_proto.jello`     |
| Tuple             | `(p0, p1)`                   | `match/tuple_basic.jello`, `match/tuple_wildcard.jello`                |
| Array exact       | `[p0, p1]`                   | —                                                                      |
| Array head/tail   | `[h \| rest]`                | `match/array_head_tail.jello`                                          |
| Array prefix/rest | `[p0, p1, ...rest]`          | `match/array_prefix_rest.jello`                                        |
| When guard        | `pat when (cond) => {...}`   | `match/fallthrough_when.jello`, `match/fallthrough_when_no_expr.jello` |
| Fallthrough       | `pat,` (no `=>`)             | `match/fallthrough_when.jello`                                         |
| Dynamic scalar    | Match on `Any` numeric/bool  | `match/dynamic_scalar.jello`                                           |

### 4.4 With (Elixir-style)

| Feature         | Description                        | Tests                        |
| --------------- | ---------------------------------- | ---------------------------- |
| All match       | `with p1 <- e1, p2 <- e2 { body }` | `with/basic.jello`           |
| First fails     | Else runs                          | `with/first_fails.jello`     |
| Second fails    | Else runs                          | `with/second_fails.jello`    |
| No else         | Returns failure value              | `with/no_else.jello`         |
| Exhaustive else | Last arm `_ => ...`                | `with/exhaustive_else.jello` |

---

## 5. Functions and Closures

### 5.1 Functions

| Feature       | Description          | Tests                              |
| ------------- | -------------------- | ---------------------------------- |
| Function expr | `fn(x) { ... }`      | `fn/infer_param_numeric_add.jello` |
| Typed params  | `fn(x: I32) { ... }` | `closure_call.jello`               |
| Return        | `return expr;`       | `function/body_locals.jello`       |
| Tail expr     | Block tail as return | `function/tail_expr.jello`         |
| Void return   | No value             | `function/return_void.jello`       |

### 5.2 Closures

| Feature          | Description                  | Tests                                                                                       |
| ---------------- | ---------------------------- | ------------------------------------------------------------------------------------------- |
| Capture          | Free vars in closure         | `fn/capture_no_params.jello`, `fn/capture_raw_caps.jello`, `function/closure_capture.jello` |
| Nested           | Closure in closure           | `fn/infer_nested_fn_capture_and_param.jello`                                                |
| Call through var | `let f = fn(...){...}; f(x)` | `closure_call.jello`                                                                        |

### 5.3 Calls

| Feature         | Description           | Tests                                         |
| --------------- | --------------------- | --------------------------------------------- |
| Direct          | `f(x)`                | `call/basic.jello`                            |
| Callee expr     | `(choose())(x)`       | `call/callee_expr.jello`                      |
| In control flow | Call in `if`, `while` | `call/simple_if.jello`, `call/in_while.jello` |
| Large arity     | Many args             | `call/large_arity.jello`                      |

---

## 6. Objects and Prototypes

### 6.1 Object Basics

| Feature        | Description          | Tests                         |
| -------------- | -------------------- | ----------------------------- |
| Literal        | `{a: 1, b: "hi"}`    | `object/literal.jello`        |
| Get            | `obj.field`          | `object/get.jello`            |
| Assign         | `obj.field = v`      | `object/assign.jello`         |
| Add member     | Dynamic add          | `object/add_member.jello`     |
| Dynamic access | `obj[expr]` on `Any` | `object/dynamic_access.jello` |

### 6.2 Prototypes

| Feature          | Description               | Tests                                                                           |
| ---------------- | ------------------------- | ------------------------------------------------------------------------------- |
| Prototype syntax | `proto { m() { ... } }`   | `object/prototype_syntax_basic.jello`, `object/prototype_syntax_template.jello` |
| Prototype sugar  | `proto { m() { ... } }`   | `object/prototype_sugar_basic.jello`, `object/prototype_sugar_template.jello`   |
| Delegation       | Property lookup via proto | `object/prototype_delegation.jello`                                             |
| As type          | `proto` as type           | `object/prototype_as_type.jello`                                                |

### 6.3 Methods and `this`

| Feature      | Description              | Tests                           |
| ------------ | ------------------------ | ------------------------------- |
| Method call  | `obj.m()` binds `this`   | `object/method_call_this.jello` |
| Const method | `const m = fn() { ... }` | `object/method_const_fun.jello` |
| Across fn    | Method passed to fn      | `object/across_fn.jello`        |

### 6.4 Instantiation

| Feature          | Description                  | Tests                                                                           |
| ---------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| `new`            | `new Proto()`                | `object/new_calls_init.jello`                                                   |
| `new` with args  | `new Proto(a, b)`            | `object/new_calls_init_args.jello`                                              |
| Template proto   | `new Proto<T>()`             | `object/new_template_proto_init.jello`, `object/new_template_proto_infer.jello` |
| Template ops     | Operations on template types | `object/template_ops.jello`                                                     |
| Runtime metadata | Template at runtime          | `object/template_runtime_metadata.jello`                                        |

---

## 7. Modules and Imports

| Feature       | Description                   | Tests                        |
| ------------- | ----------------------------- | ---------------------------- |
| Main          | Entry module                  | `module/main.jello`          |
| Consts        | Module-level const            | `module/consts.jello`        |
| Import        | `import "path"`               | `module/math.jello`          |
| Named imports | `import { a, b } from "path"` | `module/named_imports.jello` |

---

## 8. Exceptions

| Feature     | Description            | Tests                                              |
| ----------- | ---------------------- | -------------------------------------------------- |
| `try/catch` | Catch throws and traps | `try-catch/basic.jello`, `try-catch/minimal.jello` |
| `throw`     | Explicit throw         | `assert/caught.jello`                              |
| Uncaught    | No handler             | `assert/uncaught.jello` (expect fail)              |

---

## 9. Const and Static

| Feature               | Description       | Tests                                               |
| --------------------- | ----------------- | --------------------------------------------------- |
| `const`               | Immutable binding | `const/basic_fold.jello`, `const/bytes_alias.jello` |
| Assign to const fails | Compile error     | `const/assign_fails.jello` (expect fail)            |

---

## 10. Blocks and Scoping

| Feature      | Description          | Tests                  |
| ------------ | -------------------- | ---------------------- |
| Block expr   | `{ stmt* expr }`     | `block/expr.jello`     |
| Let in block | `let x = e` in scope | `expr/let_in_if.jello` |

---

## 11. Indexing

| Feature            | Description          | Tests                                                                   |
| ------------------ | -------------------- | ----------------------------------------------------------------------- |
| Array `[i]`        | Index by `i32`       | `array/index_sugar.jello`                                               |
| Array `[i]` i8/i16 | Index by smaller int | `array/index_sugar_i8_index.jello`, `array/index_sugar_i16_index.jello` |
| Bytes `[i]`        | Index bytes          | `bytes/index_sugar_i16_index.jello`                                     |

---

## 12. Recursion

| Feature | Description          | Tests                         |
| ------- | -------------------- | ----------------------------- |
| Basic   | Self-call            | `recursion/basic.jello`       |
| Tail    | Tail call            | `recursion/tail.jello`        |
| Mutual  | A calls B, B calls A | `recursion/tail_mutual.jello` |

---

## 13. Coverage Gaps (Resolved)

| Area              | Tests                                    | Notes                                 |
| ----------------- | ---------------------------------------- | ------------------------------------- |
| `do..while`       | `while/do_while.jello`                   | Body runs at least once               |
| Match bind        | `match/bind.jello`                       | `y => { use y }` binds subject        |
| Match array exact | `match/array_exact.jello`                | `[a, b] => {...}`                     |
| List patterns     | `match/list_head_tail.jello`             | `[h \| t]` on list                    |
| Negative type     | `errors/implicit_narrow_i32_to_i8.jello` | Compiler rejects i32→i8 (expect fail) |
| `Any` coercion    | `bytes/to_bytes_builtin.jello`           | `Integer.to_bytes`, `Float.to_bytes`  |
| Module re-export  | `module/reexport.jello`                  | Export imported binding               |
| REPL              | `jelloc/tests/integration/repl.rs`       | Incremental parse/exec                |

**Deferred**: Float→int NaN/Inf trap — VM asserts on NaN; needs VM trap path.

---

## 14. Test Execution

- **jelloc tests**: Compile `.jello` → `.jlo`, run on VM, expect `"ok"` return.
- **Negative tests**: `assert/uncaught.jello`, `const/assign_fails.jello`, `errors/implicit_narrow_i32_to_i8.jello` expect failure.
- **Run**: `ctest --test-dir build` (or `-R jelloc` for jelloc-only).
- **Add test**: Place `.jello` in `ctest/<feature>/`; CMake auto-registers via `file(GLOB_RECURSE ...)`.

---

## 15. Summary

Jello is a **statically typed prototypal language** with:

- **Types**: Primitives (`i8`–`i64`, `f16`–`f64`, `bool`, `atom`), heap types (`bytes`, `list`, `array`, `object`, `fun`), and `Any`
- **Inference**: Locals and params; bidirectional; no global HM
- **Objects**: Prototypal with `this`; `new Proto()`; templates
- **Control**: `if`, `while`, `do..while`, `break`/`continue`, `match`, `with`
- **Functions**: First-class; closures; tail recursion
- **Strings**: UTF-8 `bytes`; interpolation; Unicode escapes
- **Exceptions**: `try/catch`, `throw`; VM traps caught

The `ctest/` suite covers most features. Use this checklist to identify gaps and to describe the language when adapting external tests or onboarding contributors.
