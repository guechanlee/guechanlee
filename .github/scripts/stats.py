"""Generate small SVG stat cards (stats + top languages) from the public GitHub API."""
import json
import os
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "guechanlee")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "dist")


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-stats",
            **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


user = api(f"/users/{USER}")
repos, page = [], 1
while True:
    chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
    repos += chunk
    if len(chunk) < 100:
        break
    page += 1
own = [r for r in repos if not r["fork"]]
stars = sum(r["stargazers_count"] for r in own)
try:
    commits = api(f"/search/commits?q=author:{USER}&per_page=1")["total_count"]
except Exception:
    commits = None

# Languages are ranked by how many repositories use them (not by bytes), so one
# repo with a committed virtualenv or generated files cannot dominate the chart.
EXCLUDE_REPOS = {x for x in os.environ.get("EXCLUDE_REPOS", "flask_ex").split(",") if x}
IGNORE_LANGS = {"Batchfile", "PowerShell", "Shell", "XSLT", "Dockerfile", "Go Template", "C"}
langs = {}
for r in own:
    if r["name"] in EXCLUDE_REPOS or r["name"] == USER:
        continue
    try:
        used = api(f"/repos/{USER}/{r['name']}/languages")
    except Exception:
        continue
    for k in used:
        if k not in IGNORE_LANGS:
            langs[k] = langs.get(k, 0) + 1

FONT = "font-family=\"'Segoe UI',Ubuntu,'Noto Sans KR',sans-serif\""
BORDER = "#e4e2e2"


def card(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect x="0.5" y="0.5" rx="8" width="{w-1}" height="{h-1}" fill="#fffefe" stroke="{BORDER}"/>'
        f"{body}</svg>"
    )


rows = [
    ("Public Repos", len(own)),
    ("Total Stars", stars),
    ("Followers", user["followers"]),
    ("Commits (public)", commits if commits is not None else "-"),
]
body = f'<text x="24" y="34" {FONT} font-size="17" font-weight="600" fill="#2563eb">{escape(USER)}\'s GitHub Stats</text>'
for i, (k, v) in enumerate(rows):
    y = 68 + i * 26
    body += f'<text x="24" y="{y}" {FONT} font-size="13" fill="#434d58">{escape(k)}</text>'
    body += f'<text x="260" y="{y}" {FONT} font-size="13" font-weight="700" fill="#1f2937" text-anchor="end">{escape(str(v))}</text>'
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8").write(card(284, 170, body))

total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
palette = ["#2563eb", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#64748b"]
body = f'<text x="24" y="34" {FONT} font-size="17" font-weight="600" fill="#2563eb">Top Languages <tspan font-size="11" font-weight="400" fill="#6b7280">(by repos)</tspan></text>'
x, bar_w = 24, 252
for i, (k, v) in enumerate(top):
    w = max(2, round(bar_w * v / total))
    body += f'<rect x="{x}" y="50" width="{w}" height="10" fill="{palette[i]}"/>'
    x += w
for i, (k, v) in enumerate(top):
    col, row = divmod(i, 3)
    cx, cy = 24 + col * 130, 88 + row * 24
    body += f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{palette[i]}"/>'
    body += f'<text x="{cx+16}" y="{cy}" {FONT} font-size="12" fill="#434d58">{escape(k)} {v*100/total:.1f}%</text>'
open(os.path.join(OUT, "langs.svg"), "w", encoding="utf-8").write(card(284, 170, body))
print("ok", len(own), stars, commits, top[:3])
