import os, re, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
django.setup()
from django.urls import get_resolver

def walk(patterns, prefix=""):
    for p in patterns:
        if hasattr(p, "url_patterns"):
            yield from walk(p.url_patterns, prefix + str(p.pattern))
        else:
            yield prefix + str(p.pattern), p.callback

def perm_names(perms):
    out = []
    for p in perms:
        if isinstance(p, type):
            out.append(p.__name__)
        else:
            text = repr(p)
            names = re.findall(r"<class '[\w.]+\.(\w+)'>", text)
            out.append(" | ".join(names) if names else type(p).__name__)
    return ", ".join(out) or "—"

rows = {}
for route, cb in walk(get_resolver().url_patterns):
    if "format" in route or route.startswith("admin") or "__debug__" in route:
        continue
    cls = getattr(cb, "cls", None) or getattr(cb, "view_class", None)
    path = "/" + re.sub(r"\(\?P<(\w+)>[^)]+\)", r"{\1}", route).replace("^", "").replace("$", "")
    path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", path)
    actions = getattr(cb, "actions", None)
    methods = ", ".join(sorted(m.upper() for m in actions)) if actions else ""
    if cls is None:
        rows.setdefault(path, ("function " + cb.__name__, methods, "—"))
        continue
    if not methods:
        methods = ", ".join(m.upper() for m in ("get", "post", "put", "patch", "delete") if hasattr(cls, m))
    perms = perm_names(getattr(cls, "permission_classes", []))
    key = path
    prev = rows.get(key)
    if prev:
        methods = ", ".join(sorted(set(prev[1].split(", ")) | set(methods.split(", ")) - {""}))
    rows[key] = (f"{cls.__module__.split('.')[0]}.{cls.__name__}", methods, perms)

print("| Path | Methods | View | Permission classes |")
print("|---|---|---|---|")
for path in sorted(rows):
    view, methods, perms = rows[path]
    print(f"| `{path}` | {methods} | {view} | {perms} |")
print(f"\n{len(rows)} routes.")
