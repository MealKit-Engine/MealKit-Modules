#pragma once

#include "mealkit/core/Reflect.h"

// Example simulation state and function. Replace with your own.
// Module functions take only the module's own state and plain values (never the game's World), so they stay deterministic
// and the game decides where the state lives (a WorldState or Pawn field) and when to call them (World::step()).
namespace mymodule {

using mealkit::u32;

MEALKIT_STRUCT(Counter) {
    MEALKIT_FIELD(u32, value, 0, "Value");
    MEALKIT_FIELD(u32, limit, 10, "Limit");
};

// Adds one; returns true when the limit was reached this time.
inline bool add(Counter& c) {
    if (c.value >= c.limit) return false;
    ++c.value;
    return c.value == c.limit;
}

} // namespace mymodule
