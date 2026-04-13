add_executable(jello_bench
  jello_bench.c
)

target_link_libraries(jello_bench PRIVATE jellovm)

