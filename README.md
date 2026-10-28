# MealKit-Modules

The list of source modules for [MealKit](https://github.com/MealKit-Engine/MealKit) games. Official modules and everyone else's are listed the same way. A module is **official** when its repository belongs to the `MealKit-Engine` organization; entries cannot claim it.

Each module lives in its own repository. This repository holds only:

| Path | What |
|---|---|
| `entries/<name>.txt` | One file per module: name, repository, author. Added by pull request |
| `index.json` | The full list, rebuilt by CI from each module's `v*` tags and `module.txt`. The engine tools, MealKit Manager and the editor read it |
| `template/` | Starting files for a new module (`tools/new_module.py`) |
| `.github/workflows/module.yml` | The shared module CI: builds a module's tests against the engine and runs SimCheck |
| `tools/` | `build_index.py` (check entries, build `index.json`), `check_module.ps1` (what the shared CI runs), `new_module.py` |

## Make a module

```
python tools/new_module.py <name> <folder> --author "<you>" --owner <github owner>
```

Write the code in `sim/` (deterministic, takes only the module's own state), `view/` and `assets/`, document it in `docs/index.md`, then push and tag `v0.1.0` (same as `version` in `module.txt`). The template's `.github/workflows/ci.yml` runs the shared CI on every push.

Check locally the same way CI does (with a compiler environment, for example a Visual Studio x64 prompt):

```
powershell -File tools/check_module.ps1 -Module <module folder> -Engine <MealKit folder>
```

## Register a module

Add `entries/<name>.txt` in a pull request:

```
@format module-entry 1
name cooldown
repo https://github.com/MealKit-Engine/module-cooldown
author MealKit
```

The name is first come, first served. Version, summary, tags, engine version and requirements come from the module's tags and `module.txt`, never from the entry. CI checks the entry and every `v*` tag (`module.txt` name and version match the tag, `LICENSE`, `docs/index.md`), then builds the newest tag with the shared workflow. A person reads the pull request and merges it after CI passes. CI does not review the code: a module runs inside the editor and the game, so read what you add.

The repository must be public. Once a version is listed, do not move its tag; publish a new version instead.
