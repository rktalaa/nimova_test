# nimova_test — deployment notes

Static site served by **GitHub Pages** from `main` (root) at
**https://d2c-test.talaabrands.team**.

Design filenames are NOT the deployed filenames.

Two page shapes live here:

- **Bundles** — single files exported from Claude Design, all assets inlined as
  base64 (~1–1.6 MB each). `product.html`, `b_home.html`.
- **Native** — the dc source served directly, with `support.js` and the images
  as real files under a source directory. `index.html` (from `src/`) and
  `a_home.html` + `a_product.html` (from `src-a/`). See "Why the native pages
  are native".

## Files — do not delete

| File | Purpose |
|---|---|
| `index.html` | Homepage. Built **native** from `src/nimova Home.dc.html` by `tools/build-native.py`. Not a bundle — `tools/fix-export.py` does not apply to it. |
| `product.html` | Product page for the `index.html` design. Bundle. |
| `a_home.html` | The **A direction** homepage. Built **native** from `src-a/Nimova Home.dc.html`. Replaced the old bundle on 2026-08-20; `b_home.html` still holds that previous design (the two files were byte-identical). |
| `a_product.html` | The A direction's PDP, built **native** from `src-a/Nimova PDP.dc.html`. `a_home.html` links to it, so it is not optional. Not in the version switcher — the switcher is homepages only. |
| `b_home.html` | A teammate's alternative homepage direction, and the last copy of the **previous** homepage design. **Never overwrite from an export** — it is edited independently. |
| `.nojekyll` | **Required.** See below. |
| `tools/fix-export.py` | Applies the three export fixes below. Bundles only. |
| `tools/build-native.py` | Builds a native page from a dc source. |
| `tools/links.py` | Design-filename → deployed-filename map, shared by both tools. |
| `tools/version-switcher.html` | The switcher script, re-injected by `--switcher`. |
| `src/` | Imported Claude Design sources for the `index.html` design: `nimova Home.dc.html`, `nimova Product.dc.html`, `support.js` and the 26 `assets/` images they reference. **`index.html` serves `src/support.js` and `src/assets/` at runtime — do not delete or move them.** The bundles embed their own copies. |
| `src-a/` | Imported sources for the **A direction**: `Nimova Home.dc.html`, `Nimova PDP.dc.html`, `support.js` and the 20 `img/` images. **`a_home.html` and `a_product.html` serve `src-a/support.js` and `src-a/img/` at runtime.** `support.js` is byte-identical to `src/support.js` today; each import keeps its own copy so a future export of one pair cannot break the other. |
| `CNAME` | Custom domain. Deleting it takes the site off `d2c-test.talaabrands.team`. |

## Re-apply these to every fresh export

Claude Design exports do not carry these fixes. They have regressed multiple
times — always re-apply before pushing. **Use the tool, don't hand-patch:**

    python3 tools/fix-export.py <raw-export.html> product.html
    python3 tools/fix-export.py --switcher <raw-export.html> index.html

Pass `--switcher` for any of the three homepage variants so the floating
version switcher is re-appended — a fresh export never carries it.

It applies all three fixes below and is idempotent. It re-encodes the
`__bundler/template` JSON string, and must escape the slash in every `</`
as a `\u002F` unicode escape and write non-ASCII characters literally —
that is what the exporter does, and the tool round-trips an unmodified
export byte for byte. Encode it any other way and a literal `</script>`
ends up inside the template `<script>` element, closing it early and
breaking the entire page.

**1. Link rewrite.** Pages link to each other by design filename, which 404s:

    nimova%20Home.dc.html     ->  index.html
    nimova%20Product.dc.html  ->  product.html
    Nimova%20Home.dc.html     ->  a_home.html
    Nimova%20PDP.dc.html      ->  a_product.html

The two pairs differ only by capitalisation and Product/PDP; matching is
case-sensitive, so they do not collide. Links carry query strings
(`?sku=plate&locale=en`), which the filename-only rewrite leaves intact.

The map lives in `tools/links.py` and both tools rewrite through it, so add
any newly deployed page there. A link to a design page that is *not* deployed
is reported as unresolved rather than silently rewritten.

**2. Loading screen.** Exports ship a full-screen `<svg viewBox="0 0 1200 800">`
placeholder inside `#__bundler_thumbnail`. Replace it with:

    <div id="__bundler_msg">hang on, loading&hellip;</div>

Also set `#__bundler_thumbnail` background to `#F4EDE1` (not `#FFFFFF`), add
`display: none` to `#__bundler_loading` to hide the "Unpacking..." badge, and
style `#__bundler_msg` in Quicksand 22px `#4A443C`.

**3. In-script image paths.** The bundler rewrites `<img src>` attributes to
resource uuids, but it cannot see image paths that live inside the dc logic
script. On the product page the `imgs` array in `renderVals()` ships literal
`assets/opt-p-sb-*.jpg` paths, which 404 on the deployed site — the main
gallery image renders blank and every thumbnail click swaps in another broken
image. The fix maps each path to its uuid by matching the `alt` text against
the corresponding `<img>` tag, so the loader's uuid substitution turns them
into blob URLs like every other asset.

## Why `.nojekyll` is required

Both pages contain `{{ ... }}` sequences left over from the design prototype's
template bindings. GitHub Pages runs Jekyll by default and its Liquid parser
chokes on them — this failed the very first Pages build. `.nojekyll` disables
Jekyll. Do not remove it.

## Version switcher

`index.html`, `a_home.html` and `b_home.html` each carry a `<script>` before
`</body>` that injects a floating three-way switcher (`#__ver_switch`).
The bundle calls `document.documentElement.replaceWith()` on render, wiping the
DOM, so the switcher re-attaches via a `MutationObserver` on `document`.
Preserve this script when replacing any of those three files.

## Why the native pages are native

The Home redesign (hero slideshow with video, `category`/`film`/`instagram`
sections, عربي toggle) exists **only as dc source**. No exporter build of it
exists anywhere in the Design project: `deploy/index.html`, the project's own
`index.html`, `nimova Home.html` and `site/index.html` are all the older
design, and `deploy/` is a stored folder that re-downloading does not
regenerate. The MCP cannot fetch a bundle either — `get_file` truncates at
256 KiB and the bundles are ~1.3 MB.

So `index.html` is built straight from the source instead:

    python3 tools/build-native.py "src/nimova Home.dc.html" index.html --switcher

That rewrites `./support.js` and the 37 `assets/…` references to point at
`src/`, rewrites the design-filename links via `tools/links.py`, then appends
the version switcher. Nothing is inlined and no asset is
duplicated. React and Google Fonts load from their CDNs, which a bundle would
have inlined — so unlike the bundles, this page needs network access to
unpkg.com and fonts.googleapis.com to render fully.

The A direction arrived the same way — a zip of dc sources, no bundle — so it
is built the same way from `src-a/`:

    python3 tools/build-native.py "src-a/Nimova Home.dc.html" a_home.html --switcher
    python3 tools/build-native.py "src-a/Nimova PDP.dc.html"  a_product.html

`build-native.py` takes the image folder from whatever subdirectory the source
directory has — `assets/` in `src/`, `img/` in `src-a/` — so a new import needs
no edit to the tool. It rewrites single-quoted paths as well as double-quoted
ones: exports put `<img src>` in double quotes, but the dc logic script holds
the same paths single-quoted in its own image arrays, and those 404 just as
loudly. That is the same class of bug as export fix 3 above.

If a real export of any of these pages ever becomes available, prefer it:
rebuild with `tools/fix-export.py --switcher <export> <page>` and drop the
native build.

## Known outstanding — A direction

`src-a/img/` is 11 MB of unoptimised PNGs (`spoons.png` alone is 1.8 MB at
1090×1183). Fine for a test site, heavy for a real one — convert before any
public launch. `a_product.html` also ships the design's own placeholder tiles
("shot needed", "IN USE — …"); those are deliberate, not broken images.

## Custom domain

DNS is Cloudflare: `d2c-test` CNAME -> `rktalaa.github.io`, proxy **off**
(grey cloud). Proxying breaks GitHub's certificate issuance.

## Known outstanding

The pages carry invented "verified buyer" reviews and placeholder SKUs/prices
from the design phase. Not real copy — replace before any public launch.
