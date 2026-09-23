"""MkDocs hook: give every guide its manifest description as page metadata.

The guides ship to customers unchanged, so they carry no front matter. This
hook reads manifest.yml and sets ``page.meta["description"]`` for each guide,
which Material renders as the page's meta description and overrides/main.html
as its Open Graph description.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_descriptions: dict[str, str] = {}


def on_config(config, **kwargs):
    manifest = Path(config["config_file_path"]).parent / "manifest.yml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    _descriptions.clear()
    for group in data["groups"]:
        for page in group["pages"]:
            _descriptions[page["file"]] = page["description"]
    return config


def on_page_markdown(markdown, page, **kwargs):
    description = _descriptions.get(page.file.src_uri)
    if description and "description" not in page.meta:
        page.meta["description"] = description
    return markdown
