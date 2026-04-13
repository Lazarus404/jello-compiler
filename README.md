# Jello compiler

This directory holds **jelloc**, the reference compiler for the Jello language (Rust), plus CMake glue to build and test it alongside the **Jello VM** (`jellovm`).

[JelloVM](https://github.com/lazarus404/jellovm) is the virtual machine that this compiler compiles for. The VM must be present at **`../jellovm`** for the default **embed-vm** build (jelloc links `libjellovm` for the in-process REPL and `build.rs`).

## Layout

| Path      | Role                                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| `jelloc/` | Compiler sources (`cargo` crate)                                                         |
| `ctest/`  | C tests (VM + jelloc integration); pulled in by `jellovm`’s CMake when tests are enabled |
| `bench/`  | Lua comparison harness (`bench.py`) and optional C microbench (`JELLOVM_BUILD_BENCH`)    |
| `docs/`   | ISA, VM/compiler architecture, ABI, REPL notes                                           |

## Requirements

- **Rust** (for `jelloc`)
- **CMake** 3.16+ and a **C11** toolchain (for `jellovm` and `jelloc`’s `build.rs`)
- **`../jellovm`** checkout next to this directory

## Build (release)

From **`compiler/`**:

```bash
./release.sh
```

Produces **`build/bin/jellovm`** and **`jelloc/target/release/jelloc`**.

Debug or incremental work:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
cargo build --manifest-path jelloc/Cargo.toml
```

See **`jelloc/README.md`** for compiler architecture and `cargo` usage.

## Tests

After a CMake configure/build, from **`compiler/`**:

```bash
ctest --test-dir build --output-on-failure
```

## Benchmarks

Requires **`lua`** or **`luajit`** on `PATH`.

```bash
python3 bench/bench.py --release
```

## Documentation

- Bytecode / VM: `docs/ISA.md`, `docs/vm_architecture.md`
- Compiler pipeline: `docs/compiler_architecture.md`, `jelloc/README.md`

## License

See the BSD-style license headers in the source files (copyright Jahred Love).
