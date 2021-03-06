import taichi as ti

@ti.program_test
def test_while():
  x = ti.var(ti.f32)

  N = 1

  @ti.layout
  def place():
    ti.root.dense(ti.i, N).place(x)

  @ti.kernel
  def func():
    i = 0
    s = 0
    while i < 10:
      s += i
      i += 1
    x[0] = s

  func()
  assert x[0] == 45
