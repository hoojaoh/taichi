from . import expr
from . import impl
import copy
import numbers


def broadcast_if_scalar(func):
  def broadcasted(self, other, *args, **kwargs):
    if isinstance(other, expr.Expr) or isinstance(other, numbers.Number):
      other = self.broadcast(expr.Expr(other))
    return func(self, other, *args, **kwargs)

  return broadcasted


class Matrix:
  is_taichi_class = True

  def __init__(self, n, m=1, dt=None, empty=False):
    self.grad = None
    if isinstance(n, list):
      if not isinstance(n[0], list):
        mat = [list([expr.Expr(x)]) for x in n]
      else:
        mat = n
      self.n, self.m = len(mat), len(mat[0])
      self.entries = [x for row in mat for x in row]
    else:
      self.entries = []
      self.n = n
      self.m = m
      self.dt = dt
      if empty:
        self.entries = [None] * n * m
      else:
        if dt is None:
          for i in range(n * m):
            self.entries.append(impl.expr_init(None))
        else:
          assert not impl.inside_kernel()
          for i in range(n * m):
            self.entries.append(impl.var(dt))
          self.grad = self.make_grad()

  def is_global(self):
    results = [False for _ in self.entries]
    for i, e in enumerate(self.entries):
      if isinstance(e, expr.Expr):
        if e.ptr.is_global_var():
          results[i] = True
      assert results[i] == results[
        0], "Matrices with  mixed global/local entries are not allowed"
    return results[0]

  def assign(self, other):
    if isinstance(other, expr.Expr):
      raise Exception('Cannot assign scalar expr to Matrix/Vector.')
    if not isinstance(other, Matrix):
      other = Matrix(other)
    assert other.n == self.n and other.m == self.m
    for i in range(self.n * self.m):
      self.entries[i].assign(other.entries[i])

  def __matmul__(self, other):
    assert self.m == other.n
    ret = Matrix(self.n, other.m)
    for i in range(self.n):
      for j in range(other.m):
        ret(i, j).assign(self(i, 0) * other(0, j))
        for k in range(1, other.n):
          ret(i, j).assign(ret(i, j) + self(i, k) * other(k, j))
    return ret

  @broadcast_if_scalar
  def __div__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) / other(i, j))
    return ret

  @broadcast_if_scalar
  def __rtruediv__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(other(i, j) / self(i, j))
    return ret

  def broadcast(self, scalar):
    ret = Matrix(self.n, self.m, empty=True)
    for i in range(self.n * self.m):
      ret.entries[i] = scalar
    return ret

  @broadcast_if_scalar
  def __truediv__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) / other(i, j))
    return ret

  @broadcast_if_scalar
  def __floordiv__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) // other(i, j))
    return ret

  @broadcast_if_scalar
  def __mul__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) * other(i, j))
    return ret

  __rmul__ = __mul__

  @broadcast_if_scalar
  def __add__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) + other(i, j))
    return ret

  __radd__ = __add__

  @broadcast_if_scalar
  def __sub__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(self(i, j) - other(i, j))
    return ret

  def __neg__(self):
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(-self(i, j))
    return ret

  @broadcast_if_scalar
  def __rsub__(self, other):
    assert self.n == other.n and self.m == other.m
    ret = Matrix(self.n, self.m)
    for i in range(self.n):
      for j in range(self.m):
        ret(i, j).assign(other(i, j) - self(i, j))
    return ret

  def linearize_entry_id(self, *args):
    assert 1 <= len(args) <= 2
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
      args = args[0]
    if len(args) == 1:
      args = args + (0,)
    assert 0 <= args[0] < self.n
    assert 0 <= args[1] < self.m
    return args[0] * self.m + args[1]

  def __call__(self, *args, **kwargs):
    assert kwargs == {}
    return self.entries[self.linearize_entry_id(*args)]

  def get_entry(self, *args, **kwargs):
    assert kwargs == {}
    return self.entries[self.linearize_entry_id(*args)]

  def set_entry(self, i, j, e):
    self.entries[self.linearize_entry_id(i, j)] = e

  def place(self, snode):
    for e in self.entries:
      snode.place(e)

  def subscript(self, *indices):
    if self.is_global():
      ret = Matrix(self.n, self.m, empty=True)
      for i, e in enumerate(self.entries):
        ret.entries[i] = impl.subscript(e, *indices)
      return ret
    else:
      assert len(indices) in [1, 2]
      i = indices[0]
      if len(indices) >= 2:
        j = indices[1]
      else:
        j = 0
      return self(i, j)

  class Proxy:
    def __init__(self, mat, index):
      self.mat = mat
      self.index = index

    def __getitem__(self, item):
      if not isinstance(item, list):
        item = [item]
      return self.mat(*item)[self.index]

    def __setitem__(self, key, value):
      if not isinstance(key, list):
        key = [key]
      self.mat(*key)[self.index] = value

  # host access
  def __getitem__(self, index):
    return Matrix.Proxy(self, index)
    ret = [[] for _ in range(self.n)]
    for i in range(self.n):
      for j in range(self.m):
        ret[i].append(self(i, j)[index])
    return ret

  # host access
  def __setitem__(self, index, item):
    if not isinstance(item[0], list):
      item = [[i] for i in item]
    for i in range(self.n):
      for j in range(self.m):
        self(i, j)[index] = item[i][j]

  def copy(self):
    ret = Matrix(self.n, self.m)
    ret.entries = copy.copy(self.entries)
    return ret

  def variable(self):
    ret = self.copy()
    ret.entries = [impl.expr_init(e) for e in ret.entries]
    return ret

  def cast(self, type):
    ret = self.copy()
    for i in range(len(self.entries)):
      ret.entries[i] = impl.cast(ret.entries[i], type)
    return ret

  def abs(self):
    ret = self.copy()
    for i in range(len(self.entries)):
      ret.entries[i] = impl.abs(ret.entries[i])
    return ret

  def trace(self):
    assert self.n == self.m
    sum = self(0, 0)
    for i in range(1, self.n):
      sum = sum + self(i, i)
    return sum

  def inverse(self):
    assert self.n == 2 and self.m == 2
    inv_det = impl.expr_init(1.0 / self.determinant(self))
    return inv_det * Matrix([[self(1, 1), -self(0, 1)], [-self(1, 0), self(0, 0)]])

  @staticmethod
  def normalized(a):
    assert a.m == 1
    invlen = 1.0 / Matrix.norm(a)
    return invlen * a

  @staticmethod
  def floor(a):
    b = Matrix(a.n, a.m)
    for i in range(len(a.entries)):
      b.entries[i] = impl.floor(a.entries[i])
    return b

  @staticmethod
  def outer_product(a, b):
    assert a.m == 1
    assert b.m == 1
    c = Matrix(a.n, b.n)
    for i in range(a.n):
      for j in range(b.n):
        c(i, j).assign(a(i) * b(j))
    return c

  @staticmethod
  def transposed(a):
    ret = Matrix(a.m, a.n, empty=True)
    for i in range(a.n):
      for j in range(a.m):
        ret.set_entry(j, i, a(i, j))
    return ret

  @staticmethod
  def polar_decompose(a):
    assert a.n == 2 and a.m == 2
    x, y = a(0, 0) + a(1, 1), a(1, 0) - a(0, 1)
    scale = impl.expr_init(1.0 / impl.sqrt(x * x + y * y))
    c = x * scale
    s = y * scale
    r = Matrix([[c, -s], [s, c]])
    return r, Matrix.transposed(r) @ a

  @staticmethod
  def determinant(a):
    if a.n == 2 and a.m == 2:
      return a(0, 0) * a(1, 1) - a(0, 1) * a(1, 0)
    elif a.n == 3 and a.m == 3:
      return a(0, 0) * (a(1, 1) * a(2, 2) - a(2, 1) * a(1, 2)) - a(1, 0) * (
            a(0, 1) * a(2, 2) - a(2, 1) * a(0, 2)) + a(2, 0) * (
                   a(0, 1) * a(1, 2) - a(1, 1) * a(0, 2))

  @staticmethod
  def cross(a, b):
    assert a.n == 3 and a.m == 1
    assert b.n == 3 and b.m == 1
    return Matrix([
      a(1) * b(2) - a(2) * b(1),
      a(2) * b(0) - a(0) * b(2),
      a(0) * b(1) - a(1) * b(0),
    ])

  @staticmethod
  def diag(dim, val):
    ret = Matrix(dim, dim)
    for i in range(dim):
      for j in range(dim):
        ret.set_entry(i, j, 0)
    for i in range(dim):
      ret.set_entry(i, i, val)
    return ret

  def loop_range(self):
    return self.entries[0]

  @broadcast_if_scalar
  def augassign(self, other, op):
    if not isinstance(other, Matrix):
      other = Matrix(other)
    assert self.n == other.n and self.m == other.m
    for i in range(len(self.entries)):
      self.entries[i].augassign(other.entries[i], op)

  def atomic_add(self, other):
    assert self.n == other.n and self.m == other.m
    for i in range(len(self.entries)):
      self.entries[i].atomic_add(other.entries[i])

  def make_grad(self):
    ret = Matrix(self.n, self.m, empty=True)
    for i in range(len(ret.entries)):
      ret.entries[i] = self.entries[i].grad
    return ret

  def sum(self):
    ret = self.entries[0]
    for i in range(1, len(self.entries)):
      ret = ret + self.entries[i]
    return ret

  def norm(self, l=2):
    assert l == 2
    return impl.sqrt(self.norm_sqr())

  def norm_sqr(self):
    return impl.sqr(self).sum()

  def max(self):
    ret = self.entries[0]
    for i in range(1, len(self.entries)):
      ret = impl.max(ret, self.entries[i])
    return ret

  def min(self):
    ret = self.entries[0]
    for i in range(1, len(self.entries)):
      ret = impl.min(ret, self.entries[i])
    return ret

  def dot(self, other):
    assert self.m == 1 and other.m == 1
    return (self.transposed(self) @ other).subscript(0, 0)
