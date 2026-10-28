# __TITLE__

One paragraph: what this module gives a game, and when to use it.

- Version 0.1.0, engine __ENGINE__, no required modules
- State: `mymodule::Counter`
- Simulation: `sim/Counter.h`, screen: `view/CounterView.h`

## Adding

```
tools\module.ps1 add -Project <your project> https://github.com/__OWNER__/module-mymodule#v0.1.0
```

Then connect it to your game. Put the state in your simulation state and call the module from `World::step()`:

```cpp
// source/sim/World.h
#include "mymodule/sim/Counter.h"
// in your Pawn or WorldState:
MEALKIT_FIELD(mymodule::Counter, counter, {}, "Counter");
```

## Reference

| Function | What it does |
|---|---|
| `add(Counter&)` | Adds one; true when the limit was reached this time |
| `fill(const Counter&)` | 0..1 for a fill bar (view) |
