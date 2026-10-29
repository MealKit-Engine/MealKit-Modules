"""Creates a new module repo from the template (template/).

  python tools/new_module.py <name> <folder> --author "<name>" [--owner <GitHub owner>] [--title "<title>"] [--engine 0.5]

The name is lowercase letters/digits/_ (it becomes the folder name, C++ namespace, and asset path prefix). After creating, do git init, the first commit, and the v0.1.0 tag yourself.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from build_index import NAME_RE, RESERVED  # noqa: E402  (same name rules as the submission check)

TEXT = {".txt", ".h", ".hpp", ".cpp", ".md", ".yml", ".ui", ""}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("dest")
    ap.add_argument("--author", required=True)
    ap.add_argument("--owner", default="", help="GitHub owner for links (default: author)")
    ap.add_argument("--title", default="")
    ap.add_argument("--engine", default="0.5", help="engine MAJOR.MINOR")
    a = ap.parse_args()

    if not NAME_RE.match(a.name) or a.name in RESERVED:
        sys.exit(f"name '{a.name}' must be 2-32 of a-z 0-9 _, start with a letter, and not be reserved")
    if not re.match(r"^\d+\.\d+$", a.engine):
        sys.exit("--engine must be MAJOR.MINOR")
    if os.path.exists(a.dest) and os.listdir(a.dest):
        sys.exit(f"{a.dest} is not empty")

    subs = {"__TITLE__": a.title or a.name.replace("_", " ").title(), "__AUTHOR__": a.author,
            "__OWNER__": a.owner or a.author, "__YEAR__": str(datetime.date.today().year),
            "__ENGINE__": a.engine, "mymodule": a.name}
    src = os.path.join(ROOT, "template")
    for dirpath, _, files in os.walk(src):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), src)
            out = os.path.join(a.dest, rel.replace("mymodule", a.name))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.splitext(f)[1] in TEXT or f.startswith("."):
                with open(os.path.join(dirpath, f), encoding="utf-8") as fin:
                    text = fin.read()
                for k, v in subs.items():
                    text = text.replace(k, v)
                with open(out, "w", encoding="utf-8", newline="\n") as fout:
                    fout.write(text)
            else:
                shutil.copyfile(os.path.join(dirpath, f), out)
    print(f"created module '{a.name}' in {a.dest}")
    print("next: git init, commit, tag v0.1.0, push; then a pull request adding entries/%s.txt" % a.name)


if __name__ == "__main__":
    main()
