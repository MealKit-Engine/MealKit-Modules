# Checks one module repo (called by the shared workflow module.yml, and run locally with the same command).
#   module.txt format, LICENSE/docs/index.md → builds and runs the module's tests/ linked against the engine core → checks sim/ with SimCheck
#   pwsh tools/check_module.ps1 -Module <module folder> -Engine <engine folder> [-Build <build folder>]
# The caller sets up the compiler (Windows: vcvars64 or msvc-dev-cmd, Linux/macOS: clang). Works with both Windows PowerShell 5.1 and pwsh.
param(
    [Parameter(Mandatory)][string]$Module,
    [Parameter(Mandatory)][string]$Engine,
    [string]$Build = ""
)
$ErrorActionPreference = "Stop"
$Module = (Resolve-Path $Module).Path
$Engine = (Resolve-Path $Engine).Path
if (-not $Build) { $Build = Join-Path $Module "build/check" }
$failed = 0
function Fail([string]$msg) { Write-Host "FAIL $msg" -ForegroundColor Red; $script:failed++ }
function Pass([string]$msg) { Write-Host "ok   $msg" }

# module.txt (the engine's cmake/MealKit.cmake and the registry's tools/build_index.py read it with the same rules)
$info = @{}
$mt = Join-Path $Module "module.txt"
if (-not (Test-Path $mt)) { Fail "module.txt is missing"; exit 1 }
$lines = Get-Content $mt -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") }
if ($lines[0] -ne "@format module 1") { Fail "module.txt must start with '@format module 1'" }
foreach ($l in $lines | Select-Object -Skip 1) { $k, $v = $l -split " ", 2; $info[$k] = "$v".Trim() }
$name = $info["name"]
if ($name -notmatch '^[a-z][a-z0-9_]{1,31}$') { Fail "module.txt name '$name' must be 2-32 of a-z 0-9 _"; exit 1 }
if ($info["version"] -notmatch '^\d+\.\d+\.\d+$') { Fail "module.txt version '$($info["version"])' must be MAJOR.MINOR.PATCH" }
if ($info["engine"] -notmatch '^\d+\.\d+$') { Fail "module.txt engine '$($info["engine"])' must be MAJOR.MINOR" }
if (-not (Get-ChildItem $Module -Filter "LICENSE*" -File)) { Fail "LICENSE is missing" }
if (-not (Test-Path (Join-Path $Module "docs/index.md"))) { Fail "docs/index.md is missing" }
if (-not (Test-Path (Join-Path $Module "tests/CMakeLists.txt"))) { Fail "tests/CMakeLists.txt is missing (module unit tests)" }
if ($failed) { exit 1 }
Pass "module.txt: $name $($info["version"]), engine $($info["engine"])"

# Placed under modules/<name>/ like in a project (SimCheck --modules, #include "<name>/...")
$stage = Join-Path $Build "modules/$name"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
foreach ($item in @("module.txt", "sim", "view", "assets", "docs")) {
    $src = Join-Path $Module $item
    if (Test-Path $src) { Copy-Item $src $stage -Recurse }
}

# Module tests
$tests = Join-Path $Build "tests"
$cfg = @("-S", (Join-Path $Module "tests"), "-B", $tests, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
         "-DMEALKIT_ROOT=$Engine", "-DMEALKIT_HEADLESS_ONLY=ON")
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") { $cfg += @("-DCMAKE_C_COMPILER=clang", "-DCMAKE_CXX_COMPILER=clang++") }
& cmake @cfg
if ($LASTEXITCODE -ne 0) { Fail "configure tests"; exit 1 }
& cmake --build $tests --target "${name}_tests" mealkit_simcheck
if ($LASTEXITCODE -ne 0) { Fail "build ${name}_tests"; exit 1 }
$exe = Get-ChildItem $tests -Recurse -File | Where-Object { $_.BaseName -eq "${name}_tests" -and ($_.Extension -in @(".exe", "")) } | Select-Object -First 1
& $exe.FullName
if ($LASTEXITCODE -ne 0) { Fail "${name}_tests" } else { Pass "${name}_tests" }

# SimCheck: determinism rules, no including game source/ (SIM013), no including modules not in requires (SIM014)
$simcheck = Get-ChildItem $tests -Recurse -File | Where-Object { $_.BaseName -eq "mealkit_simcheck" -and ($_.Extension -in @(".exe", "")) } | Select-Object -First 1
$simFiles = @(Get-ChildItem (Join-Path $stage "sim") -Recurse -File -Include *.h, *.hpp, *.cpp -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
if ($simFiles.Count -eq 0) {
    Pass "SimCheck (no sim/ files)"
} else {
    & $simcheck.FullName (Join-Path $Build "simcheck.stamp") --modules (Join-Path $Build "modules") @simFiles
    if ($LASTEXITCODE -ne 0) { Fail "SimCheck" } else { Pass "SimCheck ($($simFiles.Count) files)" }
}

if ($failed) { Write-Host "$failed check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host "module $name passed"
