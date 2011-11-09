from __future__ import division

import numpy as np
import loopy as lp
import pyopencl as cl

from pyopencl.tools import pytest_generate_tests_for_pyopencl \
        as pytest_generate_tests

__all__ = ["pytest_generate_tests",
    "cl" # 'cl.create_some_context'
    ]




def test_owed_barriers(ctx_factory):
    ctx = ctx_factory()

    knl = lp.make_kernel(ctx.devices[0],
            "{[i]: 0<=i<100}",
            [
                "[i:l.0] <float32> z[i] = a[i]"
                ],
            [lp.ArrayArg("a", np.float32, shape=(100,))]
            )

    kernel_gen = lp.generate_loop_schedules(knl)
    kernel_gen = lp.check_kernels(kernel_gen)

    for gen_knl in kernel_gen:
        compiled = lp.CompiledKernel(ctx, gen_knl)
        print compiled.code




def test_wg_too_small(ctx_factory):
    ctx = ctx_factory()

    knl = lp.make_kernel(ctx.devices[0],
            "{[i]: 0<=i<100}",
            [
                "[i:l.0] <float32> z[i] = a[i]"
                ],
            [lp.ArrayArg("a", np.float32, shape=(100,))],
            local_sizes={0: 16})

    kernel_gen = lp.generate_loop_schedules(knl)
    kernel_gen = lp.check_kernels(kernel_gen)

    for gen_knl in kernel_gen:
        try:
            lp.CompiledKernel(ctx, gen_knl)
        except RuntimeError, e:
            assert "implemented and desired" in str(e)
            pass # expected!
        else:
            assert False # expecting an error




def test_multi_cse(ctx_factory):
    ctx = ctx_factory()

    knl = lp.make_kernel(ctx.devices[0],
            "{[i]: 0<=i<100}",
            [
                "[i] <float32> z[i] = cse(a[i]) + cse(a[i])**2"
                ],
            [lp.ArrayArg("a", np.float32, shape=(100,))],
            local_sizes={0: 16})

    knl = lp.split_dimension(knl, "i", 16, inner_tag="l.0")
    knl = lp.realize_cse(knl, None, np.float32, ["i_inner"])

    kernel_gen = lp.generate_loop_schedules(knl)
    kernel_gen = lp.check_kernels(kernel_gen)

    for gen_knl in kernel_gen:
        compiled = lp.CompiledKernel(ctx, gen_knl)
        print compiled.code




def test_bad_stencil(ctx_factory):
    ctx = ctx_factory()

    knl = lp.make_kernel(ctx.devices[0],
            "{[i,j]: 0<= i,j < 32}",
            [
                "[i] <float32> z[i,j] = -2*cse(a[i,j])"
                    " + cse(a[i,j-1])"
                    " + cse(a[i,j+1])"
                    " + cse(a[i-1,j])"
                    " + cse(a[i+1,i])" # watch out: i!
                ],
            [
                lp.ArrayArg("a", np.float32, shape=(32,32,))
                ])

    def variant_2(knl):
        knl = lp.split_dimension(knl, "i", 16, outer_tag="g.0", inner_tag="l.0")
        knl = lp.realize_cse(knl, None, np.float32, ["i_inner", "j"])
        return knl

    for variant in [variant_2]:
        kernel_gen = lp.generate_loop_schedules(variant(knl),
                loop_priority=["i_outer", "i_inner_0", "j_0"])
        kernel_gen = lp.check_kernels(kernel_gen)

        for knl in kernel_gen:
            print lp.generate_code(knl)





def test_stencil(ctx_factory):
    ctx = ctx_factory()

    knl = lp.make_kernel(ctx.devices[0],
            "{[i,j]: 0<= i,j < 32}",
            [
                "[i] <float32> z[i,j] = -2*cse(a[i,j])"
                    " + cse(a[i,j-1])"
                    " + cse(a[i,j+1])"
                    " + cse(a[i-1,j])"
                    " + cse(a[i+1,j])"
                ],
            [
                lp.ArrayArg("a", np.float32, shape=(32,32,))
                ])

    def variant_3(knl):
        knl = lp.split_dimension(knl, "i", 16, outer_tag="g.1", inner_tag="l.1")
        knl = lp.split_dimension(knl, "j", 16, outer_tag="g.0", inner_tag="l.0")
        knl = lp.realize_cse(knl, None, np.float32, ["i_inner", "j_inner"])
        return knl

    for variant in [variant_3]:
        kernel_gen = lp.generate_loop_schedules(variant(knl),
                loop_priority=["i_outer", "i_inner_0", "j_0"])
        kernel_gen = lp.check_kernels(kernel_gen)

        for knl in kernel_gen:
            print lp.generate_code(knl)




if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])
