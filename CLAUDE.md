# nimova_test — deployment notes

Static site served by **GitHub Pages** from `main` (root) at
**https://d2c-test.talaabrands.team**.

Pages are single-file bundles exported from Claude Design (all assets inlined
as base64, ~1–1.6 MB each). Design filenames are NOT the deployed filenames.

## Files — do not delete

| File | Purpose |
|---|---|
| `index.html` | Homepage. Exported from `nimova Home.dc.html`. |
| `product.html` | Product page. |
| `a_home.html`, `b_home.html` | Teammates' alternative homepage directions. **Never overwrite from an export** — they are edited independently. |
| `.nojekyll` | **Required.** See below. |
| `tools/fix-export.py` | Applies the three export fixes below. |
| `tools/version-switcher.html` | The switcher script, re-injected by `--switcher`. |
| `src/` | The imported Claude Design source for the product page: `nimova Product.dc.html`, `support.js` and the 14 `assets/` images it references. Reference copies — the deployed page embeds its own. |
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

**1. Link rewrite.** Exports link to the design filename, which 404s:

    nimova%20Home.dc.html  ->  index.html

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

## Re-exporting the homepage

`deploy/index.html` in the Design project is ~1.3 MB, and the design MCP's
`get_file` truncates at 256 KiB — so the homepage bundle cannot be pulled
down through the MCP. Download the project zip from claude.ai/design instead
(it contains `deploy/index.html` and `deploy/product.html`), then:

    python3 tools/fix-export.py --switcher deploy/index.html index.html

## Custom domain

DNS is Cloudflare: `d2c-test` CNAME -> `rktalaa.github.io`, proxy **off**
(grey cloud). Proxying breaks GitHub's certificate issuance.

## Known outstanding

The pages carry invented "verified buyer" reviews and placeholder SKUs/prices
from the design phase. Not real copy — replace before any public launch.
