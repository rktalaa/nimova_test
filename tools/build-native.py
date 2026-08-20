#!/usr/bin/env python3
"""Build a deployable page from a Claude Design dc source, without bundling.

    python3 tools/build-native.py "src/nimova Home.dc.html" index.html [--switcher]

The dc source runs as-is in a browser: support.js resolves React through
window.__resources with a CDN fallback, and the reel images through the
<meta name="ext-resource-dependency"> tags with an assets/ path fallback. So
the only thing standing between the source and a deployable page is that its
relative paths are written for the source directory, while the page is served
from the repo root. This rewrites them to point back at that directory — no
asset is duplicated.

The image folder is whatever subdirectory the source directory actually has
(`assets/` in src/, `img/` in src-a/), so a new import needs no edit here.
Paths are rewritten in single as well as double quotes: exports put <img src>
in double quotes but the same paths appear single-quoted inside the dc logic
script, and those 404 just as loudly.

Use this when there is no exporter build available. A real Claude Design
export is a single self-contained bundle; run tools/fix-export.py on that
instead. See CLAUDE.md.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SWITCHER = os.path.join(HERE, "version-switcher.html")
sys.path.insert(0, HERE)
from links import rewrite_links  # noqa: E402


def main():
    argv = sys.argv[1:]
    want_switcher = "--switcher" in argv
    argv = [a for a in argv if a != "--switcher"]
    if len(argv) != 2:
        sys.exit(__doc__)
    src_path, out_path = argv

    base = os.path.dirname(src_path).replace(os.sep, "/")
    if not base:
        sys.exit("error: source must live in a subdirectory (e.g. src/)")
    src = open(src_path, encoding="utf-8").read()
    log = []

    # The export's image folder(s): every subdirectory of the source directory.
    asset_dirs = sorted(d for d in os.listdir(base)
                        if os.path.isdir(os.path.join(base, d)))
    if not asset_dirs:
        sys.exit(f"error: {base}/ has no image subdirectory")

    # ./support.js -> src/support.js
    src, n_js = re.subn(r'(["\'])\./support\.js\1',
                        lambda m: f'{m.group(1)}{base}/support.js{m.group(1)}', src)
    # every "assets/… or 'img/… -> the same path under base/
    # (img src, meta content, and the JS logic script's own image arrays)
    n_assets = 0
    for d in asset_dirs:
        src, n = re.subn(r'(["\'])' + re.escape(d) + r'/',
                         lambda m, d=d: f'{m.group(1)}{base}/{d}/', src)
        n_assets += n
    log.append(f"rewrote {n_js} support.js ref, {n_assets} "
               f"{'/'.join(asset_dirs)} refs -> {base}/")

    # Pages link to each other by design filename, which 404s once deployed.
    src = rewrite_links(src, log)
    for line in log:
        print("  " + line)

    dirs_alt = "|".join(re.escape(d) + "/" for d in asset_dirs)
    leftover = re.findall(r'["\'](?:\./)?(?:' + dirs_alt + r'|support\.js)', src)
    if leftover:
        sys.exit(f"error: {len(leftover)} unrewritten path(s) remain")

    if want_switcher:
        if "__ver_switch" in src:
            print("  version switcher already present")
        else:
            block = open(SWITCHER, encoding="utf-8").read().strip()
            i = src.rfind("</body>")
            if i == -1:
                sys.exit("error: no </body> to append the version switcher to")
            src = src[:i].rstrip("\n") + "\n" + block + "\n\n" + src[i:]
            print("  appended the version switcher")

    # Every referenced file must actually exist at the rewritten path.
    root = os.path.dirname(os.path.abspath(out_path))
    refs = re.findall(r'["\'](' + re.escape(base) + r'/[^"\']+)["\']', src)
    missing = [p for p in sorted(set(refs))
               if not os.path.exists(os.path.join(root, p))]
    if missing:
        sys.exit("error: referenced file(s) not found: " + ", ".join(missing))

    open(out_path, "w", encoding="utf-8").write(src)
    print(f"  wrote {out_path} ({len(src):,} chars)")


if __name__ == "__main__":
    main()
