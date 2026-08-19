#!/usr/bin/env python3
"""Apply the nimova_test deployment fixes to a raw Claude Design export.

Claude Design exports do not carry these fixes and have regressed multiple
times (see CLAUDE.md). Run this on every fresh export before pushing:

    python3 tools/fix-export.py <raw-export.html> <output.html>
    python3 tools/fix-export.py --switcher <raw-export.html> index.html

Pass --switcher when the output is one of the three homepage variants
(index.html, a_home.html, b_home.html) so the floating version switcher is
re-appended; a fresh export never carries it.

Idempotent — safe to re-run on an already-fixed file.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SWITCHER = os.path.join(HERE, "version-switcher.html")
sys.path.insert(0, HERE)
from links import rewrite_links  # noqa: E402

LOAD_CSS_OLD = "#__bundler_loading { position: fixed;"
LOAD_CSS_NEW = "#__bundler_loading { display: none; position: fixed;"
THUMB_BG_OLD = "justify-content: center; background: #FFFFFF; z-index: 9999; }"
THUMB_BG_NEW = "justify-content: center; background: #F4EDE1; z-index: 9999; }"
THUMB_SVG_CSS = "    #__bundler_thumbnail svg { width: 100%; height: 100%; object-fit: contain; }\n"
MSG_CSS = (
    "    #__bundler_msg { font-family: 'Quicksand', system-ui, sans-serif; font-size: 22px;"
    " letter-spacing: .01em; color: #4A443C; animation: __bundler_pulse 1.6s ease-in-out infinite; }\n"
    "    @keyframes __bundler_pulse { 0%,100% { opacity: .55 } 50% { opacity: 1 } }\n"
    "    @media (prefers-reduced-motion: reduce) { #__bundler_msg { animation: none; opacity: .8 } }\n"
)
MSG_HTML = '<div id="__bundler_msg">hang on, loading&hellip;</div>'

TPL_RE = re.compile(r'(<script type="__bundler/template">\s*)(".*?")(\s*</script>)', re.S)
IMG_RE = re.compile(r'<img\s+src="([0-9a-f-]{36})"\s+alt="([^"]*)"')
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def fix_shell(src, log):
    """Loading screen: brand background, hidden 'Unpacking...' badge, text placeholder."""
    if LOAD_CSS_OLD in src:
        src = src.replace(LOAD_CSS_OLD, LOAD_CSS_NEW, 1)
        log.append("hid the 'Unpacking...' badge")
    if THUMB_BG_OLD in src:
        src = src.replace(THUMB_BG_OLD, THUMB_BG_NEW, 1)
        log.append("thumbnail background -> #F4EDE1")
    if THUMB_SVG_CSS in src:
        src = src.replace(THUMB_SVG_CSS, MSG_CSS, 1)
        log.append("replaced thumbnail svg CSS with #__bundler_msg styling")
    # Swap the full-screen SVG placeholder for the loading message.
    m = re.search(r'(<div id="__bundler_thumbnail">\s*)(<svg .*?</svg>)(\s*</div>)', src, re.S)
    if m:
        src = src[:m.start(2)] + MSG_HTML + src[m.end(2):]
        log.append("replaced loading SVG with 'hang on, loading...'")
    return src


def fix_template(tpl, log):
    """Link rewrite + resolve asset paths left inside the dc logic script."""
    tpl = rewrite_links(tpl, log)

    # The bundler rewrites <img src> attributes to uuids but cannot see image
    # paths inside the dc logic script, so those ship as literal 'assets/...'
    # and 404 once deployed. Map them back via their alt text, which the
    # bundler leaves intact on the corresponding <img> tag.
    alt_to_uuid = {alt: uuid for uuid, alt in IMG_RE.findall(tpl)}
    fixed = []
    for path, alt in re.findall(r'\["(assets/[^"]+)",\s*"([^"]*)"\]', tpl):
        uuid = alt_to_uuid.get(alt)
        if not uuid:
            log.append(f"WARNING: no <img> alt match for {path!r} — left as-is")
            continue
        tpl = tpl.replace(f'["{path}", "{alt}"]', f'["{uuid}", "{alt}"]')
        fixed.append(path)
    if fixed:
        log.append(f"resolved {len(fixed)} in-script asset path(s) to uuids: {', '.join(fixed)}")

    # A path used as the `|| "assets/…"` fallback beside a window.__resources
    # lookup is deliberate: the page declares that image with an
    # <meta name="ext-resource-dependency"> tag and resolves it through the
    # resource map at runtime. Only flag paths with no such safety net.
    declared = set(re.findall(r'__resources\.\w+\)\s*\|\|\s*"(assets/[^"]+)"', tpl))
    leftover = sorted(set(re.findall(r'assets/[A-Za-z0-9_.-]+', tpl)) - declared)
    if leftover:
        log.append(f"WARNING: unresolved asset path(s) remain: {', '.join(leftover)}")
    return tpl


def encode_template(tpl):
    """Re-encode the template exactly the way the exporter does.

    The template is a JSON string living inside a <script> element, so any
    literal '</script>' in it would close that element early and shred the
    rest of the document. The exporter escapes every '/' after '<' as \\u002F;
    json.dumps does not, so re-apply it here.
    """
    return json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")


def add_switcher(src, log):
    """Re-append the three-way homepage version switcher."""
    if "__ver_switch" in src:
        log.append("version switcher already present")
        return src
    block = open(SWITCHER, encoding="utf-8").read().strip()
    i = src.rfind("</body>")
    if i == -1:
        log.append("WARNING: no </body> — version switcher NOT added")
        return src
    log.append("re-appended the version switcher")
    return src[:i].rstrip("\n") + "\n" + block + "\n\n" + src[i:]


def main():
    argv = sys.argv[1:]
    want_switcher = "--switcher" in argv
    argv = [a for a in argv if a != "--switcher"]
    if len(argv) != 2:
        sys.exit(__doc__)
    src = open(argv[0], encoding="utf-8").read()
    log = []

    src = fix_shell(src, log)

    m = TPL_RE.search(src)
    if not m:
        sys.exit("error: no __bundler/template block found — is this a Design export?")
    tpl = fix_template(json.loads(m.group(2)), log)
    src = src[:m.start(2)] + encode_template(tpl) + src[m.end(2):]

    if want_switcher:
        src = add_switcher(src, log)

    open(argv[1], "w", encoding="utf-8").write(src)
    if log:
        for line in log:
            print("  " + line)
    else:
        print("  no changes needed — already fixed")
    print(f"  wrote {argv[1]} ({len(src):,} chars)")


if __name__ == "__main__":
    main()
