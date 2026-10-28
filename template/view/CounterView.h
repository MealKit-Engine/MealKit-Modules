#pragma once

#include "mymodule/sim/Counter.h"

// Screen-side helpers read the simulation state and never change it.
namespace mymodule {

inline float fill(const Counter& c) { return c.limit ? float(c.value) / float(c.limit) : 1.0f; }

} // namespace mymodule
