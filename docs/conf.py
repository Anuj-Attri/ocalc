"""Sphinx configuration for the ocalc documentation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytorch_sphinx_theme2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "ocalc"
author = "Anuj Attri"
release = "0.1.0"
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

exclude_patterns = ["_build"]
nitpicky = False

autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

html_theme = "pytorch_sphinx_theme2"
html_title = "ocalc"
html_static_path = []
html_extra_path = ["_extra"]
html_theme_options = {
    "pytorch_project": "docs",
    "logo": {"text": "ocalc"},
    "show_toc_level": 2,
    "show_lf_footer": False,
    "show_pytorch_org_link": False,
    "llm_disabled": True,
    "article_header_end": [],
    "article_footer_items": [],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Anuj-Attri/ocalc",
            "icon": "fa-brands fa-github",
        },
    ],
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "use_edit_page_button": True,
    "header_links_before_dropdown": 4,
}
html_context = {
    "github_url": "https://github.com",
    "github_user": "Anuj-Attri",
    "github_repo": "ocalc",
    "github_version": "main",
    "doc_path": "docs",
    "pytorch_project": "docs",
    "theme_variables": pytorch_sphinx_theme2.get_theme_variables(),
    "library_links": [],
    "version": release,
}
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
