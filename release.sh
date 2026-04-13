#!/usr/bin/env bash
# Release build from `compiler/`: CMake builds `jellovm` from the sibling `../jellovm`
# tree (see top-level CMakeLists.txt), then Rust builds `jelloc` with embed-vm.
set -euo pipefail
cd "$(dirname "$0")"

root_vm="../jellovm"
if [[ ! -d "$root_vm" ]]; then
  echo "error: $root_vm not found — clone or place the Jello VM sources next to compiler/." >&2
  exit 1
fi

echo "Building jellovm (release, from $root_vm via CMake)..."
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

echo "Building jelloc (release)..."
cargo build --release --manifest-path jelloc/Cargo.toml

echo "Done."
echo "  jellovm: $(pwd)/build/bin/jellovm"
echo "  jelloc:  $(pwd)/jelloc/target/release/jelloc"
