#include <jello.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t* read_file(const char* path, size_t* out_size) {
  if(out_size) *out_size = 0;
  FILE* f = fopen(path, "rb");
  if(!f) return NULL;
  if(fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
  long sz = ftell(f);
  if(sz < 0) { fclose(f); return NULL; }
  if(fseek(f, 0, SEEK_SET) != 0) { fclose(f); return NULL; }
  uint8_t* data = (uint8_t*)malloc((size_t)sz);
  if(!data) { fclose(f); return NULL; }
  size_t got = fread(data, 1, (size_t)sz, f);
  fclose(f);
  if(got != (size_t)sz) { free(data); return NULL; }
  if(out_size) *out_size = (size_t)sz;
  return data;
}

static int run_and_expect_ok_bytes(const char* out_path) {
  size_t size = 0;
  uint8_t* data = read_file(out_path, &size);
  if(!data) {
    fprintf(stderr, "failed to read output bytecode: %s\n", out_path);
    return 2;
  }

  jello_bc_module* m = NULL;
  jello_bc_result r = jello_bc_read(data, size, &m);
  free(data);
  if(r.err != JELLO_BC_OK) {
    fprintf(stderr, "bytecode load failed: err=%d msg=%s off=%zu\n",
            (int)r.err, r.msg ? r.msg : "(null)", r.offset);
    return 1;
  }

  jello_vm* vm = jello_vm_create();
  if (!vm) {
    fprintf(stderr, "failed to create VM\n");
    jello_bc_free(m);
    return 2;
  }
  jello_value outv = jello_make_null();
  jello_exec_status st = jello_vm_exec_status(vm, m, &outv);
  if(st != JELLO_EXEC_OK) {
    fprintf(stderr, "vm trapped: code=%d msg=%s\n",
            (int)jello_vm_last_trap_code(vm),
            jello_vm_last_trap_msg(vm) ? jello_vm_last_trap_msg(vm) : "(null)");
    jello_bc_free(m);
    jello_vm_destroy(vm);
    return 1;
  }

  if(!jello_is_ptr(outv) || jello_obj_kind_of(outv) != (uint32_t)JELLO_OBJ_BYTES) {
    fprintf(stderr, "expected bytes return value\n");
    jello_bc_free(m);
    jello_vm_destroy(vm);
    return 1;
  }
  jello_bytes* b = (jello_bytes*)jello_as_ptr(outv);
  const char* want = "ok";
  if(b->length != 2 || memcmp(b->data, want, 2) != 0) {
    fprintf(stderr, "expected bytes \"ok\" (len=%u)\n", b->length);
    jello_bc_free(m);
    jello_vm_destroy(vm);
    return 1;
  }

  jello_bc_free(m);
  jello_vm_destroy(vm);
  return 0;
}

int main(int argc, char** argv) {
  if(argc != 5) {
    fprintf(stderr, "usage: %s <jelloc_bin> <backend ir> <input.jello> <out.jlo>\n",
            argv[0] ? argv[0] : "jelloc_jello_test");
    return 2;
  }
  const char* jelloc = argv[1];
  const char* backend = argv[2];
  const char* in_path = argv[3];
  const char* out_path = argv[4];

  if(strcmp(backend, "ir") != 0) {
    fprintf(stderr, "bad backend: %s\n", backend);
    return 2;
  }

  char cmd[4096];
  int n = snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\" --backend %s --out \"%s\"",
                   jelloc, in_path, backend, out_path);
  if(n <= 0 || (size_t)n >= sizeof(cmd)) {
    fprintf(stderr, "command too long\n");
    return 2;
  }

  int rc = system(cmd);
  if(rc != 0) {
    fprintf(stderr, "jelloc returned non-zero\n");
    return 1;
  }

  return run_and_expect_ok_bytes(out_path);
}

