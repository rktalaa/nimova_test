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
| `CNAME` | Custom domain. Deleting it takes the site off `d2c-test.talaabrands.team`. |

## Re-apply these to every fresh export

Claude Design exports do not carry these fixes. Both have regressed multiple
times — always re-apply before pushing.

**1. Link rewrite.** Exports link to the design filename, which 404s:

    nimova%20Home.dc.html  ->  index.html

**2. Loading screen.** Exports ship a full-screen `<svg viewBox="0 0 1200 800">`
placeholder inside `#__bundler_thumbnail`. Replace it with:

    <div id="__bundler_msg">hang on, loading&hellip;</div>

Also set `#__bundler_thumbnail` background to `#F4EDE1` (not `#FFFFFF`), add
`display: none` to `#__bundler_loading` to hide the "Unpacking..." badge, and
style `#__bundler_msg` in Quicksand 22px `#4A443C`.

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

## Custom domain

DNS is Cloudflare: `d2c-test` CNAME -> `rktalaa.github.io`, proxy **off**
(grey cloud). Proxying breaks GitHub's certificate issuance.

## Known outstanding

The pages carry invented "verified buyer" reviews and placeholder SKUs/prices
from the design phase. Not real copy — replace before any public launch.
