"""
Every endpoint the frontend calls (src/services/api.js) must resolve to a real
backend route. Catches clients written against routes that do not exist, and
literal action names that fall into a detail route's <pk> slot.
"""

import re
import unittest
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

API_JS = Path(__file__).resolve().parents[2] / "src" / "services" / "api.js"


def frontend_paths():
    src = API_JS.read_text()
    paths = set()
    for match in re.finditer(r"`\$\{API_BASE_URL\}([^`]*)`", src):
        path = match.group(1).split("?")[0]
        path = re.sub(r"\$\{(query|search)[^`]*", "", path)
        path = re.sub(r"\$\{[^}]*\?[^}]*\}", "", path)
        path = re.sub(r"\$\{[^}]+\}", "1", path)
        if path.startswith("/"):
            paths.add(path)
    return sorted(paths)


@unittest.skipUnless(API_JS.exists(), "frontend source not present")
class FrontendContractTests(SimpleTestCase):
    def test_every_frontend_endpoint_resolves(self):
        problems = []
        for path in frontend_paths():
            url = "/api" + path
            try:
                match = resolve(url)
            except Resolver404:
                problems.append(f"{url}: no route")
                continue
            view = getattr(match.func, "cls", None) or getattr(match.func, "view_class", None)
            if getattr(view, "__name__", "") == "APIRootView":
                problems.append(f"{url}: router index, not a resource")
            for key in ("pk", "id"):
                value = match.kwargs.get(key)
                if value is not None and not str(value).isdigit():
                    problems.append(f"{url}: '{value}' captured as {key} (missing action)")
        self.assertEqual(problems, [], "\n".join(problems))
