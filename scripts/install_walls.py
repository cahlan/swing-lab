#!/usr/bin/env python3
"""Write Claude Code read-deny rules for a swing archive into .claude/settings.local.json.

  python3 scripts/install_walls.py "/path/to/archive"

The measuring agents must stay blind: they may not read other swings' records, checks, roll-ups,
profiles or the golden set. The scripts still read those files; only Claude's own file reads are blocked.
"""
import json, os, sys

if len(sys.argv) != 2:
    sys.exit(__doc__)
archive = os.path.abspath(os.path.expanduser(sys.argv[1]))
if not os.path.isdir(archive):
    sys.exit("not a folder: %s" % archive)
base = "/" + archive.replace(os.sep, "/") + "/_analysis/"          # Read rules use //path for absolute paths
rules = ["Read(%s%s)" % (base, p) for p in
         ("records/**", "checks/**", "profile/**", "rollup*", "golden*")]
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "settings.local.json")
settings = json.load(open(path)) if os.path.exists(path) else {}
deny = settings.setdefault("permissions", {}).setdefault("deny", [])
for r in rules:
    if r not in deny:
        deny.append(r)
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
with open(os.path.join(os.path.dirname(path), "archive_path.txt"), "w") as f:
    f.write(archive + "\n")
print("wrote %d deny rules to %s" % (len(rules), os.path.normpath(path)))
for r in rules:
    print("  " + r)
