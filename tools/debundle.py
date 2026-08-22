#!/usr/bin/env python3
"""Turn a bundled Claude Design export back into a native page + loose assets.

    python3 tools/debundle.py <bundle.html> <out.html> <asset-dir> [--switcher]

A bundle inlines every asset as base64 in a __bundler/manifest script and
references them from the template by UUID. That makes the page enormous
(14.8 MB for the home page) and hides the images from the repo.

This extracts each manifest entry to a real file, rewrites the template's
UUID references to point at them, and writes the template out as an
ordinary page — same result as tools/build-native.py, but sourced from a
bundle when no .dc.html is available. See CLAUDE.md.
"""
import base64, json, os, re, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from links import rewrite_links  # noqa: E402

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
       "image/gif": ".gif", "image/svg+xml": ".svg",
       "font/woff2": ".woff2", "font/woff": ".woff", "video/mp4": ".mp4",
       "text/javascript": ".js", "application/javascript": ".js"}

def slug(text, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]
    return s or fallback

def main():
    argv = [a for a in sys.argv[1:] if a != "--switcher"]
    want_switcher = "--switcher" in sys.argv[1:]
    if len(argv) != 3:
        sys.exit(__doc__)
    src_path, out_path, asset_dir = argv

    raw = open(src_path, encoding="utf-8", errors="replace").read()
    man = json.loads(re.search(r'<script type="__bundler/manifest">(.*?)</script>', raw, re.S).group(1))
    tpl = json.loads(re.search(r'<script type="__bundler/template">\s*(".*?")\s*</script>', raw, re.S).group(1))
    print(f"  manifest {len(man)} entries, template {len(tpl):,} chars")

    # Prefer a name from the alt text of the first <img> using each uuid.
    alt = {}
    for u, a in re.findall(r'<img[^>]*src="([0-9a-f-]{36})"[^>]*alt="([^"]*)"', tpl):
        alt.setdefault(u, a)

    os.makedirs(asset_dir, exist_ok=True)
    rel = os.path.relpath(asset_dir, os.path.dirname(os.path.abspath(out_path)) or ".")
    written, used = 0, {}
    for uuid, entry in man.items():
        if uuid not in tpl:
            continue
        data = base64.b64decode(entry["data"])
        if entry.get("compressed"):
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)  # gzip, per the bundle loader
        ext = EXT.get(entry.get("mime", ""), ".bin")
        name = "support.js" if ext == ".js" else f"{slug(alt.get(uuid), uuid[:8])}-{uuid[:6]}{ext}"
        with open(os.path.join(asset_dir, name), "wb") as fh:
            fh.write(data)
        used[uuid] = f"{rel}/{name}".replace(os.sep, "/")
        written += 1
    print(f"  extracted {written} assets -> {asset_dir}/")

    for uuid, path in used.items():
        tpl = tpl.replace(uuid, path)
    left = re.findall(r'"[0-9a-f-]{36}"', tpl)
    if left:
        sys.exit(f"error: {len(left)} unresolved uuid reference(s) remain")

    # Pages link to each other by design filename, which 404s once deployed.
    log = []
    tpl = rewrite_links(tpl, log)
    for line in log:
        print("  " + line)

    if want_switcher and "__ver_switch" not in tpl:
        block = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "version-switcher.html"), encoding="utf-8").read().strip()
        i = tpl.rfind("</body>")
        tpl = tpl[:i].rstrip("\n") + "\n" + block + "\n\n" + tpl[i:]
        print("  appended the version switcher")

    open(out_path, "w", encoding="utf-8").write(tpl)
    print(f"  wrote {out_path} ({len(tpl):,} chars)")

if __name__ == "__main__":
    main()
