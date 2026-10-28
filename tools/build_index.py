"""MealKit 모듈 레지스트리: entries/*.txt를 검사하고 index.json을 만든다.

등록 파일에는 이름·저장소·작성자만 있다. 버전·요약·태그·엔진·의존은 모듈 저장소의 v* 태그마다
module.txt에서 읽는다(정보가 두 곳에 있지 않게). 공식 여부는 저장소 주인이 MealKit-Engine인지로만 정한다.

  python tools/build_index.py                  모든 등록 파일 검사 + index.json 쓰기
  python tools/build_index.py --check          검사만 (등록 PR)
  python tools/build_index.py --only cooldown  그 등록 파일만 (PR에서 바뀐 것)
  python tools/build_index.py --allow-local    repo에 로컬 폴더를 허용 (시험용)
  python tools/build_index.py --check --repos-json repos.json   검사한 모듈의 저장소·최신 태그 (등록 PR 빌드)

표준 라이브러리만 쓴다. git이 PATH에 있어야 한다.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL_OWNER = "MealKit-Engine"
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
# 엔진·게임과 겹치는 이름 (엔진 cmake/MealKit.cmake와 같은 목록)
RESERVED = {"mealkit", "sim", "view", "game", "assets", "modules", "std", "core", "net", "ui", "editor"}
REPO_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(\.git)?$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ENGINE_RE = re.compile(r"^\d+\.\d+$")


class Errors:
    def __init__(self):
        self.items = []

    def add(self, where, msg):
        self.items.append(f"{where}: {msg}")


def read_kv(text):
    """'@format' 줄과 '키 값' 줄. 빈 줄·# 주석은 건너뛴다. 같은 키가 두 번이면 오류."""
    fmt, kv, dup = None, {}, []
    for line in text.splitlines():
        line = line.strip().lstrip("﻿")
        if not line or line.startswith("#"):
            continue
        if line.startswith("@format"):
            fmt = line[len("@format"):].strip()
            continue
        key, _, value = line.partition(" ")
        if key in kv:
            dup.append(key)
        kv[key] = value.strip()
    return fmt, kv, dup


def git(*args, cwd=None):
    r = subprocess.run(["git", "-c", "advice.detachedHead=false", *args], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr.strip()


def remote_tags(repo):
    """{태그: 커밋}. 주석 태그는 ^{}가 가리키는 커밋을 쓴다."""
    code, out, err = git("ls-remote", "--tags", repo)
    if code != 0:
        return None, err.splitlines()[-1] if err else "git ls-remote failed"
    tags = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        name = ref[len("refs/tags/"):]
        if name.endswith("^{}"):
            tags[name[:-3]] = sha
        else:
            tags.setdefault(name, sha)
    return tags, None


def version_key(v):
    return tuple(int(x) for x in SEMVER_RE.match(v).groups())


def read_entry(path, errors, allow_local):
    where = "entries/" + os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        fmt, kv, dup = read_kv(f.read())
    file_name = os.path.splitext(os.path.basename(path))[0]
    if fmt != "module-entry 1":
        errors.add(where, "first line must be '@format module-entry 1'")
    for key in dup:
        errors.add(where, f"'{key}' appears twice")
    for key in kv:
        if key not in ("name", "repo", "author"):
            errors.add(where, f"unknown key '{key}' (an entry holds only name, repo, author; the rest comes from module.txt)")
    name, repo, author = kv.get("name", ""), kv.get("repo", ""), kv.get("author", "")
    if name != file_name:
        errors.add(where, f"name '{name}' must match the file name '{file_name}'")
    if not NAME_RE.match(name) or name in RESERVED:
        errors.add(where, f"name '{name}' must be 2-32 of a-z 0-9 _, start with a letter, and not be reserved")
    if not author:
        errors.add(where, "author is missing")
    owner = None
    m = REPO_RE.match(repo)
    if m:
        owner = m.group(1)
        repo = f"https://github.com/{m.group(1)}/{m.group(2)}"
    elif not (allow_local and os.path.isdir(repo)):
        errors.add(where, f"repo '{repo}' must be https://github.com/<owner>/<repo>")
    return {"name": name, "repo": repo, "author": author, "owner": owner, "where": where}


def check_version(entry, tag, commit, work, errors):
    """태그 하나를 받아 module.txt·LICENSE·docs/index.md를 본다. 맞으면 버전 항목, 아니면 None."""
    where = f"{entry['where']} {tag}"
    dst = os.path.join(work, f"{entry['name']}-{tag}")
    code, _, err = git("clone", "--quiet", "--depth", "1", "--branch", tag, entry["repo"], dst)
    if code != 0:
        errors.add(where, f"cannot clone: {err.splitlines()[-1] if err else 'git clone failed'}")
        return None
    mt = os.path.join(dst, "module.txt")
    if not os.path.isfile(mt):
        errors.add(where, "module.txt is missing")
        return None
    with open(mt, encoding="utf-8") as f:
        fmt, kv, _ = read_kv(f.read())
    ok = True
    if fmt != "module 1":
        errors.add(where, "module.txt must start with '@format module 1'"); ok = False
    if kv.get("name") != entry["name"]:
        errors.add(where, f"module.txt name '{kv.get('name')}' differs from the entry '{entry['name']}'"); ok = False
    if kv.get("version") != tag[1:]:
        errors.add(where, f"module.txt version '{kv.get('version')}' differs from the tag '{tag}'"); ok = False
    if not ENGINE_RE.match(kv.get("engine", "")):
        errors.add(where, f"module.txt engine '{kv.get('engine')}' must be MAJOR.MINOR"); ok = False
    licenses = [n for n in os.listdir(dst) if n.upper().startswith("LICENSE")]
    if not licenses:
        errors.add(where, "LICENSE is missing"); ok = False
    if not os.path.isfile(os.path.join(dst, "docs", "index.md")):
        errors.add(where, "docs/index.md is missing"); ok = False
    if not ok:
        return None
    requires = []
    for req in kv.get("requires", "").split():
        rname, _, rver = req.partition("@")
        requires.append({"name": rname, "version": rver} if rver else {"name": rname})
    return {
        "version": kv["version"], "tag": tag, "commit": commit, "engine": kv["engine"], "requires": requires,
        "title": kv.get("title", entry["name"]), "summary": kv.get("summary", ""),
        "tags": kv.get("tags", "").split(), "license": guess_license(os.path.join(dst, licenses[0])),
        "docs": {lang: f"docs/{f}" for lang, f in (("en", "index.md"), ("ko", "index.ko.md"))
                 if os.path.isfile(os.path.join(dst, "docs", f))},
    }


def guess_license(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.read(400)
    for spdx, marker in (("MIT", "MIT License"), ("Apache-2.0", "Apache License"), ("BSD-3-Clause", "BSD 3-Clause"),
                         ("Zlib", "zlib License"), ("MPL-2.0", "Mozilla Public License")):
        if marker.lower() in head.lower():
            return spdx
    return "other"


def build(entries, errors, previous):
    work = tempfile.mkdtemp(prefix="mealkit-registry-")
    modules = []
    try:
        for entry in entries:
            tags, err = remote_tags(entry["repo"])
            if tags is None:
                errors.add(entry["where"], f"cannot read tags of {entry['repo']}: {err}")
                continue
            old = {v["tag"]: v for v in previous.get(entry["name"], {}).get("versions", [])}
            versions = []
            for tag, commit in tags.items():
                if not (tag.startswith("v") and SEMVER_RE.match(tag[1:])):
                    continue
                if tag in old and old[tag]["commit"] != commit:
                    # 한 번 올린 버전의 태그를 옮기면 받는 쪽 커밋 검사가 깨진다. 새 버전을 내야 한다.
                    errors.add(f"{entry['where']} {tag}", f"tag moved from {old[tag]['commit'][:10]} to {commit[:10]}; publish a new version instead")
                    versions.append(old[tag])
                    continue
                v = old.get(tag) if tag in old else check_version(entry, tag, commit, work, errors)
                if v:
                    versions.append(v)
            if not versions:
                errors.add(entry["where"], "no valid v<MAJOR.MINOR.PATCH> tag")
                continue
            versions.sort(key=lambda v: version_key(v["version"]), reverse=True)
            latest = versions[0]
            modules.append({
                "name": entry["name"], "repo": entry["repo"], "author": entry["author"],
                "official": entry["owner"] == OFFICIAL_OWNER,
                "title": latest["title"], "summary": latest["summary"], "tags": latest["tags"],
                "license": latest["license"], "latest": latest["version"],
                "versions": [{k: v[k] for k in ("version", "tag", "commit", "engine", "requires", "docs")} | {"checks": v.get("checks", {})}
                             for v in versions],
            })
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return modules


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entries", default=os.path.join(ROOT, "entries"))
    ap.add_argument("--out", default=os.path.join(ROOT, "index.json"))
    ap.add_argument("--check", action="store_true", help="do not write index.json")
    ap.add_argument("--only", nargs="*", default=[], help="entry names to check")
    ap.add_argument("--allow-local", action="store_true", help="accept local folders as repo (tests)")
    ap.add_argument("--repos-json", help="write {name: {repo, tag}} of the checked modules (registry.yml build matrix)")
    args = ap.parse_args()

    errors = Errors()
    paths = sorted(os.path.join(args.entries, n) for n in os.listdir(args.entries) if n.endswith(".txt"))
    for n in os.listdir(args.entries):
        if not n.endswith(".txt") and not n.startswith("."):
            errors.add(f"entries/{n}", "entries hold only <name>.txt files")
    entries = [read_entry(p, errors, args.allow_local) for p in paths]

    seen = {}
    for e in entries:
        key = e["repo"].lower()
        if key in seen:
            errors.add(e["where"], f"repo is already registered as '{seen[key]}'")
        seen[key] = e["name"]

    previous = {}
    if os.path.isfile(args.out):
        with open(args.out, encoding="utf-8") as f:
            previous = {m["name"]: m for m in json.load(f).get("modules", [])}

    targets = [e for e in entries if not args.only or e["name"] in args.only]
    for name in args.only:
        if name not in {e["name"] for e in entries}:
            errors.add(f"entries/{name}.txt", "not found")
    if not errors.items:
        modules = build(targets, errors, previous)
        if args.repos_json:  # registry.yml이 공용 워크플로로 빌드할 모듈: {이름: {repo: owner/repo, tag}}
            repos = {m["name"]: {"repo": m["repo"].removeprefix("https://github.com/"), "tag": m["versions"][0]["tag"]}
                     for m in modules}
            with open(args.repos_json, "w", encoding="utf-8") as f:
                json.dump(repos, f, separators=(",", ":"))
        if args.only:  # 나머지는 지난 목록을 그대로 둔다
            done = {m["name"] for m in modules}
            modules += [m for n, m in previous.items() if n not in done and n in {e["name"] for e in entries}]
        modules.sort(key=lambda m: m["name"])
        for m in modules:
            print(f"ok  {m['name']} {m['latest']}{' (official)' if m['official'] else ''}  {m['repo']}")
        if not args.check and not errors.items:
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"format": 1, "modules": modules}, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print(f"wrote {args.out} ({len(modules)} modules)")

    for e in errors.items:
        print(f"error {e}", file=sys.stderr)
    return 1 if errors.items else 0


if __name__ == "__main__":
    sys.exit(main())
