#if defined(TLANG_WITH_CUDA)
#include <cuda.h>
#include "llvm_jit.h"
#include <taichi/context.h>

TLANG_NAMESPACE_BEGIN

class CUDAContext {
  CUdevice device;
  std::vector<CUmodule> cudaModules;
  CUcontext context;
  // CUlinkState linker;
  int devCount;
  CUdeviceptr context_buffer;

 public:
  CUDAContext();

  CUmodule compile(const std::string &ptx);

  CUfunction get_function(CUmodule module, const std::string &func_name);

  void launch(CUfunction func,
              void *context_ptr,
              unsigned gridDim,
              unsigned blockDim);

  ~CUDAContext();
};

extern CUDAContext cuda_context;

TLANG_NAMESPACE_END
#endif
