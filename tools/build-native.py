#!/usr/bin/env python3
"""Build a deployable page from a Claude Design dc source, without bundling.

    python3 tools/build-native.py "src/nimova Home.dc.html" index.html [--switcher]

The dc source runs as-is in a browser: support.js resolves React through
window.__resources with a CDN fallback, and the reel images through the
<meta name="ext-resource-dependency"> tags with an assets/ path fallback. So
the only thing standing between the source and a deployable page is that its
relative paths are written for src/, while the page is served from the repo
root. This rewrites them to point back at src/ — no asset is duplicated.

Use this when there is no exporter build available. A real Claude Design
export is a single self-contained bundle; run tools/fix-export.py on that
instead. See CLAUDE.md.
"""
import os
import re
import sys

SWITCHER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "version-switcher.html")


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

    # ./support.js -> src/support.js
    src, n_js = re.subn(r'"\./support\.js"', f'"{base}/support.js"', src)
    # every "assets/… -> "src/assets/…  (img src, meta content, JS fallbacks)
    src, n_assets = re.subn(r'"assets/', f'"{base}/assets/', src)
    print(f"  rewrote {n_js} support.js ref, {n_assets} asset refs -> {base}/")

    leftover = re.findall(r'"(?:\./)?(?:assets/|support\.js)', src)
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
    missing = [p for p in sorted(set(re.findall(r'"(' + re.escape(base) + r'/[^"]+)"', src)))
               if not os.path.exists(os.path.join(root, p))]
    if missing:
        sys.exit("error: referenced file(s) not found: " + ", ".join(missing))

    open(out_path, "w", encoding="utf-8").write(src)
    print(f"  wrote {out_path} ({len(src):,} chars)")


if __name__ == "__main__":
    main()
