# Jello VM Architecture

The Jello VM is a register-based, typed interpreter that executes validated bytecode modules. This document describes how the VM is structured and how execution works.

## Overview

The VM:

- Loads and validates bytecode (`.jlo` format)
- Executes via a fetch–decode–dispatch–execute loop
- Maintains typed register frames; every register has a static type from the bytecode
- Uses a mark-sweep GC for heap objects
- Supports boxing/unboxing at the `Dynamic` boundary

Bytecode format and opcode semantics are defined in `docs/ISA.md`. The public API is in `jellovm/src/include/jello.h`.

## Execution Pipeline

| Stage | Input               | Output                | Module(s)                |
| ----- | ------------------- | --------------------- | ------------------------ |
| 0     | CLI / embedder API  | Task dispatch         | `jellovm/src/main.c`     |
| 1     | Raw bytes           | Loaded module         | `jellovm/src/bytecode/loader.c` |
| 2     | Loaded module       | Validated module      | `jellovm/src/bytecode/check.c` |
| 3     | Validated module    | Execution result      | `jellovm/src/vm/interp.c` + `jellovm/src/vm/*.c` |
| 4     | Allocation requests | GC-managed objects    | `jellovm/src/gc.c`       |
| 5     | Object operations   | Values / side effects | `jellovm/src/types/*.c`  |

### Main Loop

1. **Fetch** — read `insns[pc]` (fixed 8-byte `jello_insn`)
2. **Decode** — op, a, b, c, imm (fixed layout)
3. **Dispatch** — branch to opcode handler (switch or computed goto)
4. **Execute** — handler reads/writes registers, may call runtime, push/pop frames
5. **Advance** — `pc++` or jump; check for traps and exceptions

The VM’s interpreter loop is implemented as `vm_exec_loop` (`jellovm/src/vm/ops/exec_loop.c`). It inlines a small hot subset of opcodes and falls back to the canonical dispatcher (`op_dispatch`) for everything else. For conformance/debugging, the VM can be built in a reference mode that routes all opcodes through `op_dispatch` (see `docs/vm_exec_loop.md`).

## Module Layout

The VM sources live in the **`jellovm/`** tree at the repository root (also buildable standalone). Layout:

```
jellovm/
├── src/
│   ├── main.c              # CLI entry (jellovm_cli)
│   ├── vm.c                # jello_vm_create, jello_vm_destroy, exec API
│   ├── vm/
│   │   ├── interp.c        # Main loop: fetch, dispatch, exec_entry
│   │   ├── frame.c         # reg_frame, call_frame, push/pop
│   │   ├── reg.c           # load/store for typed slots (u32, i64, f64, f16, etc.)
│   │   ├── box.c           # box_from_typed, store_from_boxed (typed↔Dynamic)
│   │   ├── spill.c         # spill_push, spill_pop (spill stack)
│   │   ├── exc.c           # Exception handling, unwind
│   │   ├── call.c          # Call setup, arg copying
│   │   └── ops/            # dispatch.c, exec_loop.c, opcode implementations
│   ├── gc.c                # Mark-sweep GC, root scanning
│   ├── bytecode/
│   │   ├── loader.c        # jello_bc_read, format parsing
│   │   └── check.c         # Validation (reg bounds, types, jump targets)
│   ├── types/              # Object implementations (bytes, list, array, object, etc.)
│   └── include/
│       ├── jello.h         # Public API (opaque types, embedder surface)
│       └── jello/
│           ├── internal.h  # Internal structures (reg_frame, bytecode layout)
│           ├── check.h
│           └── internal/   # VM-internal headers (e.g. vm_internal.h, ops_decl.h)
```

## Typed Registers

Every register has a **static type** from the function’s `reg_types[]` table. The compiler guarantees correct types; the bytecode validator enforces them. Handlers never store a value of the wrong type into a register.

- **Typed regs** — unboxed; type comes from `(function, reg_id) → type_id`
- **Dynamic regs** — store boxed `jello_value` (tagged or pointer)
- **Spill stack** — holds boxed values only; used when register pressure is high

## Frame and Register Access

- **reg_frame** — per-call frame with typed slots; layout computed from `reg_types`
- **reg_ptr(rf, r)** — pointer to slot for register `r`
- **load/store** — typed access (u32, i64, f64, f16, ptr) via `reg.c`

## Boxing and Unboxing

- **TO_DYN** — boxes a typed register into a `Dynamic` register
- **FROM*DYN*\*** — unboxes with a type check; traps on mismatch
- Boxing allocates for I64, F64, F32, F16; I8/I16/I32/Bool/Atom use tagged immediates

See `docs/boxing.md` for details.

## GC and Roots

The GC is precise and scans:

- Spill stack
- `gc_roots`
- `const_fun_cache`
- Call frames (typed slots; only pointer slots are traced)

`scan_typed_frames` interprets `reg_types` to find pointer slots. All roots must be visible during collection.

## Exception Handling

- **TRY/ENDTRY** — push/pop handler
- **THROW** — set `exc_pending`, `exc_payload`; goto exception dispatch
- **Unwind** — pop frames above handler, restore `pc`, store payload in catch register

Handler stack and call stack must stay consistent during unwind.

## Embedding

Embedders need only `#include <jello.h>`:

```c
jello_vm* vm = jello_vm_create();
jello_bc_module* m = NULL;
jello_bc_result r = jello_bc_read(data, size, &m);
if (r.err == JELLO_BC_OK) {
  jello_value out;
  jello_exec_status st = jello_vm_exec_status(vm, m, &out);
  if (st == JELLO_EXEC_OK) { /* use out */ }
}
jello_bc_free(m);
jello_vm_destroy(vm);
```

Internal structures (`reg_frame`, `call_frame`, bytecode layout) are not exposed.
