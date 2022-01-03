#!/usr/bin/env python3
import math
from show import show
def foo(n):
    return n*2
def bar(n):
    return math.log(n)

x = 42
show(foo(bar(x)))

show(
    # calling `foo`
    foo(x),
    # calling `bar`
    bar(x),
)
