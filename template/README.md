# __TITLE__ (MealKit module)

A source module for [MealKit](https://github.com/MealKit-Engine/MealKit) games. Docs: [docs/index.md](docs/index.md).

```
tools\module.ps1 add -Project <your project> mymodule
```

Tests (not copied into projects): `cmake -S tests -B build/tests -G Ninja -DMEALKIT_ROOT=<engine> -DMEALKIT_HEADLESS_ONLY=ON`, then build and run `mymodule_tests`.
To publish: push a `v<version>` tag that matches `version` in `module.txt`, then add `entries/mymodule.txt` to [MealKit-Modules](https://github.com/MealKit-Engine/MealKit-Modules) in a pull request.

MIT license.
