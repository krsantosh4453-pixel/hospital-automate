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


def _normalise(path):
    path = path.split("?")[0]
    path = re.sub(r"\$\{(query|search)[^`]*", "", path)
    path = re.sub(r"\$\{[^}]*\?[^}]*\}", "", path)
    return re.sub(r"\$\{[^}]+\}", "1", path)


def frontend_calls():
    """(method, path, line) for every request(`${API_BASE_URL}...`, {method}) call."""
    src = API_JS.read_text()
    calls = []
    pattern = r"request\(\s*`\$\{API_BASE_URL\}([^`]*)`\s*(?:,\s*\{(?P<opts>[^}]*))?"
    for match in re.finditer(pattern, src):
        method = re.search(r"method:\s*['\"](\w+)['\"]", match.group("opts") or "")
        calls.append((
            method.group(1).upper() if method else "GET",
            _normalise(match.group(1)),
            src.count("\n", 0, match.start()) + 1,
        ))
    return calls


@unittest.skipUnless(API_JS.exists(), "frontend source not present")
class FrontendMethodContractTests(SimpleTestCase):
    def test_every_frontend_call_uses_a_method_the_route_accepts(self):
        calls = frontend_calls()
        self.assertGreater(len(calls), 200, "request() calls were not found; update the pattern")
        problems = []
        for method, path, line in calls:
            try:
                match = resolve("/api" + path)
            except Resolver404:
                continue  # reported by test_every_frontend_endpoint_resolves
            actions = getattr(match.func, "actions", None)
            view = getattr(match.func, "cls", None) or getattr(match.func, "view_class", None)
            if actions is not None:
                allowed = method.lower() in actions
            else:
                allowed = view is not None and hasattr(view, method.lower())
            if not allowed:
                problems.append(f"api.js:{line} {method} /api{path}")
        self.assertEqual(problems, [], "\n".join(problems))
