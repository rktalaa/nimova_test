"""Design filename -> deployed filename.

Claude Design pages link to each other by their design filename, which 404s
once deployed (the deployed site uses different names — see CLAUDE.md). Both
tools/fix-export.py and tools/build-native.py rewrite through this map.

Keep this in sync with the "Files — do not delete" table in CLAUDE.md. A page
that is deployed under some name belongs here; a design page that is not
deployed at all (e.g. "nimova Brand Story.dc.html") deliberately does not, so
that a link to it is reported as unresolved rather than silently rewritten.
"""

LINK_MAP = {
    "nimova%20Home.dc.html": "index.html",
    "nimova%20Product.dc.html": "product.html",
    # The "A" direction is a second, separate pair of design sources whose
    # filenames differ only by capitalisation and the Product/PDP wording.
    # Matching is case-sensitive, so these do not collide with the pair above.
    "Nimova%20Home.dc.html": "a_home.html",
    "Nimova%20PDP.dc.html": "a_product.html",
    # Unencoded spaces, in case an export ever emits them.
    "nimova Home.dc.html": "index.html",
    "nimova Product.dc.html": "product.html",
    "Nimova Home.dc.html": "a_home.html",
    "Nimova PDP.dc.html": "a_product.html",
}


def rewrite_links(text, log):
    """Rewrite design-filename links, and flag any that have no mapping."""
    import re

    for design, deployed in LINK_MAP.items():
        n = text.count(design)
        if n:
            text = text.replace(design, deployed)
            log.append(f"rewrote {n} link(s) {design} -> {deployed}")

    stray = sorted(set(re.findall(r'[^"\']*?\.dc\.html', text)))
    if stray:
        log.append("WARNING: link(s) to an undeployed design page remain: "
                   + ", ".join(stray))
    return text
