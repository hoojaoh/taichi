import taichi as ti

@ti.program_test
def test_static_if():
  for val in [0, 1]:
    ti.reset()
    x = ti.var(ti.i32)

    @ti.layout
    def place():
      ti.root.dense(ti.i, 1).place(x)

    @ti.kernel
    def static():
      if ti.static(val > 0.5):
        x[0] = 1
      else:
        x[0] = 0

    static()
    assert x[0] == val

