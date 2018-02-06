import numpy as np
import loopy as lp
import pyopencl as cl
import pyopencl.array

# setup
# -----
ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

# for make_kernel calls from this file
LOOPY_KERNEL_LANGUAGE_VERSION = (2018, 1)

n = 15 * 10**6
a = cl.array.arange(queue, n, dtype=np.float32)

# create
# ------
knl = lp.make_kernel(
        "{ [i]: 0<=i<n }",
        "out[i] = 2*a[i]")

# transform
# ---------
knl = lp.split_iname(knl, "i", 128, outer_tag="g.0", inner_tag="l.0")

# execute
# -------
evt, (out,) = knl(queue, a=a)
# ENDEXAMPLE

knl = lp.add_and_infer_dtypes(knl, {"a": np.dtype(np.float32)})
print(lp.generate_code_v2(knl).device_code())
