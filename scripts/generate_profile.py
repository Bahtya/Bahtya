#!/usr/bin/env python3
"""
Bahtya GitHub Profile Telemetry & SVG Generator
Generates bespoke, animated Dark & Light SVG instrument panels from live GitHub GraphQL data.
Zero third-party dependencies — pure Python standard library.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "Bahtya"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    createdAt
    followers { totalCount }
    following { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
    repositories(first: 100, privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        name
        description
        stargazerCount
        forkCount
        primaryLanguage { name color }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}
"""

# Repos whose HTML/data dumps would skew programming language DNA
DATA_HEAVY_HTML_REPOS = {"mhxxdoc", "hdl-mr-research", "mr-research-skill", "Bahtya.github.io"}

THEMES = {
    "dark": {
        "bg": "#090C11",
        "panel": "#0F141D",
        "panel_alt": "#131A26",
        "border": "#1F2937",
        "border_hi": "#2E3C52",
        "grid": "#141C28",
        "ink": "#F1F5F9",
        "ink_sub": "#94A3B8",
        "ink_muted": "#5B6B82",
        "amber": "#F97316",
        "amber_soft": "rgba(249,115,22,0.14)",
        "cyan": "#06B6D4",
        "cyan_soft": "rgba(6,182,212,0.14)",
        "emerald": "#10B981",
        "emerald_soft": "rgba(16,185,129,0.14)",
        "violet": "#8B5CF6",
        "violet_soft": "rgba(139,92,246,0.14)",
        "pill_bg": "#151D2B",
        "heat": ["#141C27", "#123C4A", "#0E7490", "#EA580C", "#FB923C"],
        "word_top": "#FFFFFF",
        "word_bot": "#94A3B8",
        "crt_bg": "#070A0F",
    },
    "light": {
        "bg": "#F8FAFC",
        "panel": "#FFFFFF",
        "panel_alt": "#F1F5F9",
        "border": "#E2E8F0",
        "border_hi": "#CBD5E1",
        "grid": "#EDF2F7",
        "ink": "#0F172A",
        "ink_sub": "#475569",
        "ink_muted": "#94A3B8",
        "amber": "#EA580C",
        "amber_soft": "rgba(234,88,12,0.10)",
        "cyan": "#0891B2",
        "cyan_soft": "rgba(8,145,178,0.10)",
        "emerald": "#059669",
        "emerald_soft": "rgba(5,150,105,0.10)",
        "violet": "#7C3AED",
        "violet_soft": "rgba(124,58,237,0.10)",
        "pill_bg": "#F1F5F9",
        "heat": ["#E9EEF5", "#BAE6FD", "#22D3EE", "#FB923C", "#EA580C"],
        "word_top": "#0F172A",
        "word_bot": "#475569",
        "crt_bg": "#F1F5F9",
    },
}

FONT_SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, 'Liberation Mono', monospace"

FLAGSHIP_PROJECTS = [
    {
        "slug": "kestrel-agent",
        "repo": "kestrel-agent",
        "tag": "AI AGENT · RUST",
        "accent": "amber",
        "line1": "Streaming-first Rust AI agent framework with",
        "line2": "built-in memory, skills & self-evolution.",
        "icon": "agent",
    },
    {
        "slug": "vproc",
        "repo": "vproc",
        "tag": "ARM64 · RUNTIME",
        "accent": "cyan",
        "line1": "aarch64 assembly + Rust coroutine executor —",
        "line2": "multiple virtual processes in one Android app.",
        "icon": "cpu",
    },
    {
        "slug": "wps-office-offline",
        "repo": "wps-office-offline",
        "tag": "REVERSE ENG · PYTHON",
        "accent": "violet",
        "line1": "WPS Office offline debloat reverse-engineering:",
        "line2": "strips cloud, ads, AI & promos cleanly.",
        "icon": "hex",
    },
    {
        "slug": "node_modules_killer",
        "repo": "node_modules_killer",
        "tag": "NTFS MFT · TUI",
        "accent": "emerald",
        "line1": "Direct NTFS MFT scanner (usn-journal-rs) +",
        "line2": "ratatui TUI to purge node_modules instantly.",
        "icon": "disk",
    },
    {
        "slug": "agently-mail",
        "repo": "agently-mail",
        "tag": "CF WORKERS · RE",
        "accent": "cyan",
        "line1": "Cloudflare Worker driving reverse-engineered",
        "line2": "REST API for autonomous AI-agent email.",
        "icon": "relay",
    },
    {
        "slug": "listory-plus",
        "repo": "listory-plus",
        "tag": "SEARCH ENGINE · TAURI",
        "accent": "amber",
        "line1": "Lightning-fast file & content search engine",
        "line2": "for Windows powered by native Rust + Tauri.",
        "icon": "radar",
    },
]


def fetch_github_data(token: str) -> dict:
    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "bahtya-profile-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def compute_metrics(user: dict) -> dict:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]

    active_days = sum(1 for d in days if d["contributionCount"] > 0)
    peak_day = max(days, key=lambda d: d["contributionCount"]) if days else {"contributionCount": 0, "date": ""}
    cur = best = 0
    for d in days:
        if d["contributionCount"] > 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0

    week_sums = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    repos = user["repositories"]["nodes"]
    repo_map = {r["name"]: r for r in repos}
    total_stars = sum(r["stargazerCount"] for r in repos)
    public_repos = user["repositories"]["totalCount"]

    created_year = int(user["createdAt"][:4])
    now_utc = dt.datetime.now(dt.timezone.utc)
    years_active = max(1, now_utc.year - created_year)

    # Language breakdown (smartly excluding bulk HTML static archive repos)
    lang_totals: dict[str, dict] = {}
    for r in repos:
        is_html_dump = r["name"] in DATA_HEAVY_HTML_REPOS
        for edge in r["languages"]["edges"]:
            lname = edge["node"]["name"]
            lcolor = edge["node"]["color"] or "#64748B"
            size = edge["size"]
            if is_html_dump and lname == "HTML":
                continue
            if lname not in lang_totals:
                lang_totals[lname] = {"size": 0, "color": lcolor}
            lang_totals[lname]["size"] += size

    sorted_langs = sorted(lang_totals.items(), key=lambda kv: kv[1]["size"], reverse=True)[:8]
    total_bytes = sum(v["size"] for _, v in sorted_langs) or 1
    languages = [
        {
            "name": name,
            "color": info["color"],
            "pct": (info["size"] / total_bytes) * 100.0,
            "size": info["size"],
        }
        for name, info in sorted_langs
    ]

    total_commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    return {
        "total_contributions": cal["totalContributions"],
        "total_commits": total_commits,
        "public_commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "public_repos": public_repos,
        "total_stars": total_stars,
        "years_active": years_active,
        "created_year": created_year,
        "active_days": active_days,
        "total_days": len(days),
        "longest_streak": best,
        "peak_count": peak_day["contributionCount"],
        "peak_date": peak_day["date"],
        "weeks": weeks,
        "week_sums": week_sums,
        "languages": languages,
        "repo_map": repo_map,
        "updated_utc": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "updated_date": now_utc.strftime("%Y-%m-%d"),
    }


def corner_reticles(w: int, h: int, color: str, pad: int = 12, size: int = 6) -> str:
    pts = [(pad, pad), (w - pad, pad), (pad, h - pad), (w - pad, h - pad)]
    lines = []
    for x, y in pts:
        lines.append(f'<line x1="{x - size}" y1="{y}" x2="{x + size}" y2="{y}" stroke="{color}" stroke-width="1" opacity="0.65"/>')
        lines.append(f'<line x1="{x}" y1="{y - size}" x2="{x}" y2="{y + size}" stroke="{color}" stroke-width="1" opacity="0.65"/>')
    return "\n".join(lines)


def smooth_path(points: list[tuple[float, float]]) -> str:
    if len(points) < 2:
        return ""
    d = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        xm = (x0 + x1) / 2.0
        d.append(f"C {xm:.1f} {y0:.1f}, {xm:.1f} {y1:.1f}, {x1:.1f} {y1:.1f}")
    return " ".join(d)


def render_hero(m: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 1200, 360

    # Build 52-week oscilloscope curve inside x=[696..1156], y=[86..234]
    ox, oy, ow, oh = 696, 86, 460, 146
    ws = m["week_sums"] or [0] * 52
    # Log-compressed scaling so both steady activity and spikes look organic & dramatic
    logs = [math.log1p(v) for v in ws]
    max_log = max(logs) if max(logs) > 0 else 1.0
    n = len(ws)
    pts = []
    for i, lv in enumerate(logs):
        px = ox + (i / max(1, n - 1)) * ow
        py = oy + oh - 12 - (lv / max_log) * (oh - 26)
        pts.append((px, py))

    curve_d = smooth_path(pts)
    area_d = f"{curve_d} L {ox + ow:.1f} {oy + oh:.1f} L {ox:.1f} {oy + oh:.1f} Z"

    # Peak week marker
    peak_idx = max(range(n), key=lambda i: ws[i])
    peak_px, peak_py = pts[peak_idx]

    # Secondary harmonic reference wave (subtle cyan baseline)
    pts2 = []
    for i in range(n):
        px = ox + (i / max(1, n - 1)) * ow
        base = oy + oh - 18 - (0.18 + 0.10 * math.sin(i * 0.45) + 0.06 * math.cos(i * 0.9)) * (oh - 28)
        pts2.append((px, base))
    curve2_d = smooth_path(pts2)

    # KPI cells
    kpis = [
        (f"{m['total_contributions']:,}", "CONTRIBUTIONS / 365D", t["amber"]),
        (f"{m['longest_streak']} DAYS", "LONGEST STREAK", t["emerald"]),
        (f"{m['public_repos']} REPOS", "PUBLIC ARTIFACTS", t["cyan"]),
        (f"{m['years_active']} YRS", f"SHIPPING SINCE {m['created_year']}", t["violet"]),
    ]
    kpi_svg = []
    cell_w = (w - 64) / 4.0
    for idx, (val, label, acc) in enumerate(kpis):
        cx = 32 + idx * cell_w
        if idx > 0:
            kpi_svg.append(f'<line x1="{cx:.1f}" y1="278" x2="{cx:.1f}" y2="336" stroke="{t["border"]}" stroke-width="1"/>')
        kpi_svg.append(f'<rect x="{cx + 18:.1f}" y="286" width="3" height="42" rx="1.5" fill="{acc}"/>')
        kpi_svg.append(
            f'<text x="{cx + 34:.1f}" y="308" font-family="{FONT_MONO}" font-size="22" font-weight="700" fill="{t["ink"]}">{escape(val)}</text>'
        )
        kpi_svg.append(
            f'<text x="{cx + 34:.1f}" y="326" font-family="{FONT_MONO}" font-size="10.5" font-weight="600" letter-spacing="1.2" fill="{t["ink_muted"]}">{escape(label)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Bahtya — Systems Engineer, Reverse Engineering, AI Agent Architect">
  <defs>
    <pattern id="heroGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{t["grid"]}" stroke-width="1"/>
    </pattern>
    <linearGradient id="wordGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t["word_top"]}"/>
      <stop offset="100%" stop-color="{t["word_bot"]}"/>
    </linearGradient>
    <linearGradient id="accentBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["amber"]}"/>
      <stop offset="55%" stop-color="{t["cyan"]}"/>
      <stop offset="100%" stop-color="{t["emerald"]}"/>
    </linearGradient>
    <linearGradient id="waveFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t["amber"]}" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="{t["amber"]}" stop-opacity="0.01"/>
    </linearGradient>
    <linearGradient id="scanSweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["cyan"]}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{t["cyan"]}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{t["cyan"]}" stop-opacity="0"/>
    </linearGradient>
    <filter id="glowAmber" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="crtClip">
      <rect x="{ox}" y="{oy}" width="{ow}" height="{oh}" rx="8"/>
    </clipPath>
    <style>
      .pulse-led {{ animation: ledPulse 2.4s ease-in-out infinite; }}
      .blink-cur {{ animation: curBlink 1.1s steps(2, start) infinite; }}
      .scan-bar {{ animation: sweepX 6.5s linear infinite; }}
      .wave-flow {{ stroke-dasharray: 6 6; animation: dashMove 18s linear infinite; }}
      @keyframes ledPulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
      @keyframes curBlink {{ 0%,49% {{ opacity: 1; }} 50%,100% {{ opacity: 0; }} }}
      @keyframes sweepX {{ 0% {{ transform: translateX(-90px); }} 100% {{ transform: translateX({ow + 90}px); }} }}
      @keyframes dashMove {{ to {{ stroke-dashoffset: -240; }} }}
    </style>
  </defs>

  <!-- Outer Chassis -->
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="url(#heroGrid)"/>
  {corner_reticles(w, h, t["border_hi"])}

  <!-- Top Telemetry Header Bar -->
  <line x1="32" y1="48" x2="{w - 32}" y2="48" stroke="{t["border"]}" stroke-width="1"/>
  <circle cx="44" cy="30" r="6" fill="{t["emerald"]}" opacity="0.22" class="pulse-led"/>
  <circle cx="44" cy="30" r="3.2" fill="{t["emerald"]}" class="pulse-led"/>
  <text x="58" y="34" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" letter-spacing="1.4" fill="{t["ink_sub"]}">SYS.ONLINE  ·  BAHTYA // HARDWARE-TO-AGENT LAB</text>
  <text x="{w - 36}" y="34" text-anchor="end" font-family="{FONT_MONO}" font-size="11" letter-spacing="1.1" fill="{t["ink_muted"]}">FIG.01  ·  SYNC {escape(m["updated_date"])}  ·  AARCH64 / X86_64</text>

  <!-- Left Hero Identity -->
  <text x="36" y="138" font-family="{FONT_SANS}" font-size="76" font-weight="800" letter-spacing="4" fill="url(#wordGrad)">BAHTYA</text>
  <rect x="38" y="152" width="210" height="4" rx="2" fill="url(#accentBar)"/>

  <text x="38" y="185" font-family="{FONT_SANS}" font-size="17" font-weight="600" fill="{t["ink"]}">Systems Engineer · Reverse Engineering · AI Agent Architect</text>
  <text x="38" y="208" font-family="{FONT_SANS}" font-size="13.5" fill="{t["ink_sub"]}">Building from bare-metal aarch64 &amp; NTFS internals up to autonomous Rust agents.</text>

  <!-- Animated Command Pill -->
  <rect x="38" y="224" width="620" height="32" rx="6" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="52" y="244" font-family="{FONT_MONO}" font-size="11.5" fill="{t["amber"]}" font-weight="700">$</text>
  <text x="68" y="244" font-family="{FONT_MONO}" font-size="11.5" fill="{t["ink_sub"]}">cargo run --release --target aarch64  //  rust · asm · re · agents</text>
  <rect x="536" y="233" width="8" height="14" rx="1" fill="{t["cyan"]}" class="blink-cur"/>

  <!-- Right Live Oscilloscope Viewport -->
  <rect x="{ox - 12}" y="64" width="{ow + 24}" height="192" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="{ox}" y="79" font-family="{FONT_MONO}" font-size="10" font-weight="700" letter-spacing="1.2" fill="{t["ink_muted"]}">CH1 // 52-WEEK CONTRIBUTION WAVEFORM (LIVE)</text>
  <text x="{ox + ow}" y="79" text-anchor="end" font-family="{FONT_MONO}" font-size="10" font-weight="700" fill="{t["amber"]}">PEAK {m["peak_count"]}/DAY</text>

  <rect x="{ox}" y="{oy}" width="{ow}" height="{oh}" rx="8" fill="{t["crt_bg"]}" stroke="{t["border"]}"/>
  <g clip-path="url(#crtClip)">
    <!-- Oscilloscope Graticule -->
    <line x1="{ox}" y1="{oy + oh * 0.25:.1f}" x2="{ox + ow}" y2="{oy + oh * 0.25:.1f}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>
    <line x1="{ox}" y1="{oy + oh * 0.50:.1f}" x2="{ox + ow}" y2="{oy + oh * 0.50:.1f}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>
    <line x1="{ox}" y1="{oy + oh * 0.75:.1f}" x2="{ox + ow}" y2="{oy + oh * 0.75:.1f}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>
    <line x1="{ox + ow * 0.25:.1f}" y1="{oy}" x2="{ox + ow * 0.25:.1f}" y2="{oy + oh}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>
    <line x1="{ox + ow * 0.50:.1f}" y1="{oy}" x2="{ox + ow * 0.50:.1f}" y2="{oy + oh}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>
    <line x1="{ox + ow * 0.75:.1f}" y1="{oy}" x2="{ox + ow * 0.75:.1f}" y2="{oy + oh}" stroke="{t["grid"]}" stroke-dasharray="3 4"/>

    <!-- Subtle Radar Scanline -->
    <rect x="{ox}" y="{oy}" width="72" height="{oh}" fill="url(#scanSweep)" class="scan-bar"/>

    <!-- Secondary Harmonic Baseline -->
    <path d="{curve2_d}" fill="none" stroke="{t["cyan"]}" stroke-width="1.2" opacity="0.45" class="wave-flow"/>

    <!-- Real Contribution Area + Glow Curve -->
    <path d="{area_d}" fill="url(#waveFill)"/>
    <path id="mainWave" d="{curve_d}" fill="none" stroke="{t["amber"]}" stroke-width="2.2" filter="url(#glowAmber)"/>

    <!-- Peak Marker -->
    <line x1="{peak_px:.1f}" y1="{oy}" x2="{peak_px:.1f}" y2="{oy + oh}" stroke="{t["amber"]}" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"/>
    <circle cx="{peak_px:.1f}" cy="{peak_py:.1f}" r="4" fill="{t["amber"]}"/>
    <circle cx="{peak_px:.1f}" cy="{peak_py:.1f}" r="8" fill="none" stroke="{t["amber"]}" stroke-width="1" opacity="0.55" class="pulse-led"/>

    <!-- Traveling Signal Dot -->
    <circle r="3.5" fill="{t["cyan"]}" filter="url(#glowAmber)">
      <animateMotion dur="7s" repeatCount="indefinite" path="{curve_d}"/>
    </circle>
  </g>
  <text x="{ox}" y="248" font-family="{FONT_MONO}" font-size="9.5" fill="{t["ink_muted"]}">W-52</text>
  <text x="{ox + ow / 2:.1f}" y="248" text-anchor="middle" font-family="{FONT_MONO}" font-size="9.5" fill="{t["ink_muted"]}">REAL GITHUB ACTIVITY CADENCE</text>
  <text x="{ox + ow}" y="248" text-anchor="end" font-family="{FONT_MONO}" font-size="9.5" fill="{t["ink_muted"]}">NOW</text>

  <!-- Bottom KPI Strip -->
  <line x1="32" y1="270" x2="{w - 32}" y2="270" stroke="{t["border"]}" stroke-width="1"/>
  {"".join(kpi_svg)}
</svg>'''


def render_architecture(theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 1200, 350

    layers = [
        {
            "id": "L0",
            "title": "SILICON & DRIVERS",
            "accent": t["amber"],
            "soft": t["amber_soft"],
            "tags": ["aarch64 asm", "I2C HID", "NTFS MFT", "AT/Modem"],
            "desc1": "Virtual processes in ARM64,",
            "desc2": "MFT disk scans & driver fixes.",
            "repos": "vproc · eg25 · gpd-fix",
        },
        {
            "id": "L1",
            "title": "SYSTEMS & RUNTIME",
            "accent": t["cyan"],
            "soft": t["cyan_soft"],
            "tags": ["Rust", "Go", "C", "TLS Emulation"],
            "desc1": "Zero-overhead native binaries,",
            "desc2": "coroutines & custom TLS stacks.",
            "repos": "listory-plus · pplx-cli · Gomoco",
        },
        {
            "id": "L2",
            "title": "REVERSE & PROTOCOLS",
            "accent": t["violet"],
            "soft": t["violet_soft"],
            "tags": ["Binary RE", "REST / OAuth2", "CF Workers"],
            "desc1": "Dissecting closed apps & private",
            "desc2": "APIs into clean open tooling.",
            "repos": "wps-offline · agently-mail",
        },
        {
            "id": "L3",
            "title": "AI AGENTS & INTERFACES",
            "accent": t["emerald"],
            "soft": t["emerald_soft"],
            "tags": ["Agent Core", "Memory/Skills", "TUI / Web"],
            "desc1": "Streaming-first Rust AI agents,",
            "desc2": "LLM ops & terminal consoles.",
            "repos": "kestrel-agent · FalconFlow",
        },
    ]

    cards = []
    card_w = 266
    gap = 24
    start_x = 32
    top_y = 66
    card_h = 212

    for i, layer in enumerate(layers):
        cx = start_x + i * (card_w + gap)
        acc = layer["accent"]
        # Connector bus arrow between cards
        if i < len(layers) - 1:
            x1 = cx + card_w
            x2 = x1 + gap
            ym = top_y + card_h / 2
            cards.append(
                f'<line x1="{x1}" y1="{ym:.1f}" x2="{x2}" y2="{ym:.1f}" stroke="{t["border_hi"]}" stroke-width="1.5"/>'
            )
            cards.append(
                f'<line x1="{x1}" y1="{ym:.1f}" x2="{x2}" y2="{ym:.1f}" stroke="{acc}" stroke-width="2" stroke-dasharray="4 6" class="bus-flow"/>'
            )
            cards.append(f'<polygon points="{x2 - 4},{ym - 3.5:.1f} {x2},{ym:.1f} {x2 - 4},{ym + 3.5:.1f}" fill="{acc}"/>')

        # Card body
        cards.append(f'<rect x="{cx}" y="{top_y}" width="{card_w}" height="{card_h}" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>')
        cards.append(f'<rect x="{cx}" y="{top_y}" width="{card_w}" height="3" rx="1.5" fill="{acc}"/>')

        # Layer ID badge
        cards.append(f'<rect x="{cx + 16}" y="{top_y + 18}" width="32" height="20" rx="4" fill="{layer["soft"]}"/>')
        cards.append(f'<text x="{cx + 32}" y="{top_y + 32}" text-anchor="middle" font-family="{FONT_MONO}" font-size="10.5" font-weight="700" fill="{acc}">{layer["id"]}</text>')
        cards.append(f'<text x="{cx + 55}" y="{top_y + 32}" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="0.4" fill="{t["ink"]}">{escape(layer["title"])}</text>')

        # Tags (2 rows of 2 pills)
        for ti, tag in enumerate(layer["tags"]):
            col = ti % 2
            row = ti // 2
            pw = 112
            px = cx + 16 + col * (pw + 10)
            py = top_y + 52 + row * 28
            cards.append(f'<rect x="{px}" y="{py}" width="{pw}" height="22" rx="4" fill="{t["pill_bg"]}" stroke="{t["border"]}" stroke-width="0.8"/>')
            cards.append(f'<text x="{px + pw / 2:.1f}" y="{py + 14.5}" text-anchor="middle" font-family="{FONT_MONO}" font-size="10" fill="{t["ink_sub"]}">{escape(tag)}</text>')

        # Description
        cards.append(f'<text x="{cx + 16}" y="{top_y + 132}" font-family="{FONT_SANS}" font-size="12.5" fill="{t["ink_sub"]}">{escape(layer["desc1"])}</text>')
        cards.append(f'<text x="{cx + 16}" y="{top_y + 150}" font-family="{FONT_SANS}" font-size="12.5" fill="{t["ink_sub"]}">{escape(layer["desc2"])}</text>')

        # Repo footer inside card
        cards.append(f'<line x1="{cx + 16}" y1="{top_y + 168}" x2="{cx + card_w - 16}" y2="{top_y + 168}" stroke="{t["border"]}" stroke-width="0.8"/>')
        cards.append(f'<circle cx="{cx + 22}" cy="{top_y + 189}" r="3" fill="{acc}"/>')
        cards.append(f'<text x="{cx + 32}" y="{top_y + 193}" font-family="{FONT_MONO}" font-size="10.5" fill="{t["ink_muted"]}">{escape(layer["repos"])}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Engineering Architecture Stack — L0 Silicon to L3 AI Agents">
  <defs>
    <pattern id="archGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{t["grid"]}" stroke-width="1"/>
    </pattern>
    <linearGradient id="busGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["amber"]}"/>
      <stop offset="33%" stop-color="{t["cyan"]}"/>
      <stop offset="66%" stop-color="{t["violet"]}"/>
      <stop offset="100%" stop-color="{t["emerald"]}"/>
    </linearGradient>
    <style>
      .bus-flow {{ animation: busMove 2.2s linear infinite; }}
      .rail-flow {{ stroke-dasharray: 10 14; animation: railMove 8s linear infinite; }}
      @keyframes busMove {{ to {{ stroke-dashoffset: -20; }} }}
      @keyframes railMove {{ to {{ stroke-dashoffset: -240; }} }}
    </style>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="url(#archGrid)"/>
  {corner_reticles(w, h, t["border_hi"])}

  <!-- Header -->
  <text x="34" y="36" font-family="{FONT_MONO}" font-size="12" font-weight="700" letter-spacing="1.4" fill="{t["ink"]}">FIG.02 // ENGINEERING STACK — BARE METAL TO AUTONOMOUS AGENTS</text>
  <text x="{w - 34}" y="36" text-anchor="end" font-family="{FONT_MONO}" font-size="11" letter-spacing="1" fill="{t["ink_muted"]}">FULL-STACK VERTICAL OWNERSHIP</text>
  <line x1="32" y1="48" x2="{w - 32}" y2="48" stroke="{t["border"]}" stroke-width="1"/>

  {"".join(cards)}

  <!-- Bottom System Bus Rail -->
  <rect x="32" y="294" width="{w - 64}" height="36" rx="8" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <line x1="56" y1="312" x2="{w - 56}" y2="312" stroke="{t["border_hi"]}" stroke-width="1.5"/>
  <line x1="56" y1="312" x2="{w - 56}" y2="312" stroke="url(#busGrad)" stroke-width="2" class="rail-flow"/>
  <rect x="430" y="301" width="340" height="22" rx="4" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="600" y="315.5" text-anchor="middle" font-family="{FONT_MONO}" font-size="10.5" font-weight="600" letter-spacing="1.2" fill="{t["ink_sub"]}">HARDWARE ⇄ KERNEL/FS ⇄ RE/PROTOCOLS ⇄ AI AGENTS</text>
</svg>'''


def render_telemetry(m: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 1200, 336

    # Left panel: 53-week contribution matrix
    lx, ly, lw, lh = 32, 64, 712, 246
    weeks = m["weeks"]
    cell = 10
    step = 12.6
    grid_x = lx + 20
    grid_y = ly + 46

    def heat_level(c: int) -> int:
        if c <= 0:
            return 0
        if c <= 3:
            return 1
        if c <= 12:
            return 2
        if c <= 35:
            return 3
        return 4

    matrix_cells = []
    for wi, week in enumerate(weeks[-53:]):
        for day in week["contributionDays"]:
            wd = day["weekday"]
            lvl = heat_level(day["contributionCount"])
            cx = grid_x + wi * step
            cy = grid_y + wd * step
            cls = ' class="hot-cell"' if lvl == 4 else ""
            matrix_cells.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="2.2" fill="{t["heat"][lvl]}"{cls}/>'
            )

    # Legend squares
    leg_x = lx + lw - 134
    leg_y = ly + 22
    legend_svg = [f'<text x="{leg_x - 8}" y="{leg_y + 8}" text-anchor="end" font-family="{FONT_MONO}" font-size="9.5" fill="{t["ink_muted"]}">LESS</text>']
    for i, col in enumerate(t["heat"]):
        legend_svg.append(f'<rect x="{leg_x + i * 14}" y="{leg_y}" width="10" height="10" rx="2" fill="{col}"/>')
    legend_svg.append(f'<text x="{leg_x + 76}" y="{leg_y + 8}" font-family="{FONT_MONO}" font-size="9.5" fill="{t["ink_muted"]}">MORE</text>')

    # Sub-metrics under matrix
    sub_stats = [
        ("COMMITS", f"{m['total_commits']:,}", t["amber"]),
        ("PULL REQUESTS", f"{m['prs']:,}", t["cyan"]),
        ("ISSUES", f"{m['issues']:,}", t["violet"]),
        ("ACTIVE DAYS", f"{m['active_days']}/{m['total_days']}", t["emerald"]),
    ]
    sub_svg = []
    sw = (lw - 40) / 4.0
    for idx, (lbl, val, acc) in enumerate(sub_stats):
        sx = lx + 20 + idx * sw
        sub_svg.append(f'<rect x="{sx:.1f}" y="{ly + 168}" width="{sw - 10:.1f}" height="58" rx="6" fill="{t["panel_alt"]}" stroke="{t["border"]}"/>')
        sub_svg.append(f'<text x="{sx + 12:.1f}" y="{ly + 193}" font-family="{FONT_MONO}" font-size="16" font-weight="700" fill="{t["ink"]}">{escape(val)}</text>')
        sub_svg.append(f'<circle cx="{sx + 15:.1f}" cy="{ly + 211}" r="2.8" fill="{acc}"/>')
        sub_svg.append(f'<text x="{sx + 24:.1f}" y="{ly + 214.5}" font-family="{FONT_MONO}" font-size="9.5" font-weight="600" letter-spacing="0.8" fill="{t["ink_muted"]}">{escape(lbl)}</text>')

    # Right panel: Language DNA Spectrum
    rx, ry, rw, rh = 764, 64, 404, 246
    langs = m["languages"]
    bar_x, bar_y, bar_w, bar_h = rx + 20, ry + 52, rw - 40, 14

    bar_segs = []
    cur_x = bar_x
    for i, lang in enumerate(langs):
        seg_w = max(4.0, (lang["pct"] / 100.0) * bar_w)
        if i == len(langs) - 1:
            seg_w = max(2.0, bar_x + bar_w - cur_x)
        bar_segs.append(f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{lang["color"]}"/>')
        cur_x += seg_w

    # 2-column language legend
    lang_rows = []
    for i, lang in enumerate(langs[:8]):
        col = i % 2
        row = i // 2
        lx_item = rx + 20 + col * 188
        ly_item = ry + 96 + row * 34
        lang_rows.append(f'<circle cx="{lx_item + 5}" cy="{ly_item}" r="4.5" fill="{lang["color"]}"/>')
        lang_rows.append(f'<text x="{lx_item + 17}" y="{ly_item + 4}" font-family="{FONT_MONO}" font-size="12" font-weight="600" fill="{t["ink"]}">{escape(lang["name"])}</text>')
        lang_rows.append(f'<text x="{lx_item + 172}" y="{ly_item + 4}" text-anchor="end" font-family="{FONT_MONO}" font-size="11.5" fill="{t["ink_muted"]}">{lang["pct"]:.1f}%</text>')
        lang_rows.append(f'<line x1="{lx_item}" y1="{ly_item + 14}" x2="{lx_item + 172}" y2="{ly_item + 14}" stroke="{t["border"]}" stroke-width="0.7" opacity="0.6"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Live GitHub Contribution Matrix and Language DNA">
  <defs>
    <pattern id="telGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{t["grid"]}" stroke-width="1"/>
    </pattern>
    <clipPath id="barClip">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7"/>
    </clipPath>
    <linearGradient id="shimmer" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <style>
      .hot-cell {{ animation: heatPulse 3.2s ease-in-out infinite; }}
      .bar-shimmer {{ animation: shimmerSlide 4.5s ease-in-out infinite; }}
      @keyframes heatPulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.72; }} }}
      @keyframes shimmerSlide {{ 0% {{ transform: translateX(-80px); }} 100% {{ transform: translateX({bar_w + 80}px); }} }}
    </style>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="url(#telGrid)"/>
  {corner_reticles(w, h, t["border_hi"])}

  <!-- Header -->
  <text x="34" y="36" font-family="{FONT_MONO}" font-size="12" font-weight="700" letter-spacing="1.4" fill="{t["ink"]}">FIG.03 // LIVE TELEMETRY &amp; CODEBASE DNA</text>
  <text x="{w - 34}" y="36" text-anchor="end" font-family="{FONT_MONO}" font-size="11" letter-spacing="1" fill="{t["ink_muted"]}">REAL GITHUB GRAPHQL FEED  ·  NO STATIC MOCKS</text>
  <line x1="32" y1="48" x2="{w - 32}" y2="48" stroke="{t["border"]}" stroke-width="1"/>

  <!-- Left Matrix Panel -->
  <rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="{lx + 20}" y="{ly + 29}" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1" fill="{t["ink_sub"]}">53-WEEK ACTIVITY MATRIX ({m["total_contributions"]:,} EVENTS)</text>
  {"".join(legend_svg)}
  {"".join(matrix_cells)}
  {"".join(sub_svg)}

  <!-- Right Language Panel -->
  <rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="{rx + 20}" y="{ry + 29}" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1" fill="{t["ink_sub"]}">LANGUAGE SPECTRUM (PUBLIC CODE)</text>
  <g clip-path="url(#barClip)">
    {"".join(bar_segs)}
    <rect x="{bar_x}" y="{bar_y}" width="64" height="{bar_h}" fill="url(#shimmer)" class="bar-shimmer"/>
  </g>
  {"".join(lang_rows)}
</svg>'''


def schematic_icon(kind: str, acc: str, muted: str) -> str:
    if kind == "agent":
        return f'''
        <g transform="translate(492, 46)" opacity="0.9">
          <line x1="16" y1="16" x2="48" y2="34" stroke="{muted}" stroke-width="1.3"/>
          <line x1="16" y1="52" x2="48" y2="34" stroke="{muted}" stroke-width="1.3"/>
          <line x1="48" y1="34" x2="68" y2="16" stroke="{acc}" stroke-width="1.5"/>
          <line x1="48" y1="34" x2="68" y2="52" stroke="{acc}" stroke-width="1.5"/>
          <circle cx="16" cy="16" r="5" fill="{muted}"/>
          <circle cx="16" cy="52" r="5" fill="{muted}"/>
          <circle cx="48" cy="34" r="7" fill="{acc}"/>
          <circle cx="68" cy="16" r="4.5" fill="{acc}" opacity="0.8"/>
          <circle cx="68" cy="52" r="4.5" fill="{acc}" opacity="0.8"/>
        </g>'''
    if kind == "cpu":
        return f'''
        <g transform="translate(496, 46)" opacity="0.9">
          <rect x="14" y="14" width="40" height="40" rx="5" fill="none" stroke="{acc}" stroke-width="1.8"/>
          <rect x="24" y="24" width="20" height="20" rx="2" fill="{acc}" opacity="0.22" stroke="{acc}" stroke-width="1.2"/>
          <line x1="24" y1="6" x2="24" y2="14" stroke="{muted}" stroke-width="1.5"/>
          <line x1="34" y1="6" x2="34" y2="14" stroke="{acc}" stroke-width="1.5"/>
          <line x1="44" y1="6" x2="44" y2="14" stroke="{muted}" stroke-width="1.5"/>
          <line x1="24" y1="54" x2="24" y2="62" stroke="{muted}" stroke-width="1.5"/>
          <line x1="34" y1="54" x2="34" y2="62" stroke="{acc}" stroke-width="1.5"/>
          <line x1="44" y1="54" x2="44" y2="62" stroke="{muted}" stroke-width="1.5"/>
          <line x1="6" y1="24" x2="14" y2="24" stroke="{muted}" stroke-width="1.5"/>
          <line x1="6" y1="34" x2="14" y2="34" stroke="{acc}" stroke-width="1.5"/>
          <line x1="6" y1="44" x2="14" y2="44" stroke="{muted}" stroke-width="1.5"/>
          <line x1="54" y1="24" x2="62" y2="24" stroke="{muted}" stroke-width="1.5"/>
          <line x1="54" y1="34" x2="62" y2="34" stroke="{acc}" stroke-width="1.5"/>
          <line x1="54" y1="44" x2="62" y2="44" stroke="{muted}" stroke-width="1.5"/>
        </g>'''
    if kind == "hex":
        return f'''
        <g transform="translate(496, 46)" opacity="0.9">
          <polygon points="34,6 58,20 58,48 34,62 10,48 10,20" fill="none" stroke="{acc}" stroke-width="1.8"/>
          <polygon points="34,18 48,26 48,42 34,50 20,42 20,26" fill="{acc}" opacity="0.18" stroke="{muted}" stroke-width="1.2"/>
          <text x="34" y="38" text-anchor="middle" font-family="{FONT_MONO}" font-size="11" font-weight="700" fill="{acc}">0xFF</text>
        </g>'''
    if kind == "disk":
        return f'''
        <g transform="translate(496, 46)" opacity="0.9">
          <circle cx="34" cy="34" r="26" fill="none" stroke="{muted}" stroke-width="1.5"/>
          <circle cx="34" cy="34" r="16" fill="none" stroke="{acc}" stroke-width="1.6" stroke-dasharray="16 8"/>
          <circle cx="34" cy="34" r="5" fill="{acc}"/>
          <line x1="34" y1="34" x2="54" y2="16" stroke="{acc}" stroke-width="1.8"/>
        </g>'''
    if kind == "relay":
        return f'''
        <g transform="translate(494, 48)" opacity="0.9">
          <rect x="6" y="14" width="56" height="38" rx="5" fill="none" stroke="{acc}" stroke-width="1.8"/>
          <polyline points="8,16 34,36 60,16" fill="none" stroke="{acc}" stroke-width="1.6"/>
          <circle cx="56" cy="14" r="5" fill="{acc}"/>
        </g>'''
    # radar
    return f'''
    <g transform="translate(496, 46)" opacity="0.9">
      <circle cx="30" cy="30" r="20" fill="none" stroke="{acc}" stroke-width="1.8"/>
      <circle cx="30" cy="30" r="9" fill="{acc}" opacity="0.18" stroke="{muted}" stroke-width="1.2"/>
      <line x1="45" y1="45" x2="60" y2="60" stroke="{acc}" stroke-width="3" stroke-linecap="round"/>
    </g>'''


def render_project_card(proj: dict, m: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 584, 168
    acc = t[proj["accent"]]
    soft = t[f"{proj['accent']}_soft"]

    repo_data = m["repo_map"].get(proj["repo"], {})
    stars = repo_data.get("stargazerCount", 0)
    lang = (repo_data.get("primaryLanguage") or {}).get("name", "Code")
    lang_color = (repo_data.get("primaryLanguage") or {}).get("color") or acc

    star_str = f"★ {stars}" if stars > 0 else "OPEN SOURCE"
    tag_pill_w = max(144, int(len(proj["tag"]) * 7.6 + 26))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(proj['repo'])}">
  <defs>
    <pattern id="cardGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="{t["grid"]}" stroke-width="0.9"/>
    </pattern>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="11" fill="url(#cardGrid)" opacity="0.65"/>
  <rect x="0.5" y="18" width="3.5" height="{h - 36}" rx="1.75" fill="{acc}"/>

  <!-- Category Pill -->
  <rect x="22" y="18" width="{tag_pill_w}" height="22" rx="4" fill="{soft}"/>
  <text x="33" y="33" font-family="{FONT_MONO}" font-size="10.5" font-weight="700" letter-spacing="0.8" fill="{acc}">{escape(proj["tag"])}</text>

  <!-- Star / Status Pill -->
  <rect x="{w - 120}" y="18" width="98" height="22" rx="4" fill="{t["pill_bg"]}" stroke="{t["border"]}" stroke-width="0.8"/>
  <text x="{w - 71}" y="33" text-anchor="middle" font-family="{FONT_MONO}" font-size="10.5" font-weight="600" fill="{t["ink_sub"]}">{escape(star_str)}</text>

  <!-- Repo Title -->
  <text x="22" y="72" font-family="{FONT_MONO}" font-size="22" font-weight="700" fill="{t["ink"]}">{escape(proj["repo"])}</text>

  <!-- Description -->
  <text x="22" y="99" font-family="{FONT_SANS}" font-size="13.5" fill="{t["ink_sub"]}">{escape(proj["line1"])}</text>
  <text x="22" y="119" font-family="{FONT_SANS}" font-size="13.5" fill="{t["ink_sub"]}">{escape(proj["line2"])}</text>

  <!-- Footer meta -->
  <circle cx="28" cy="145" r="4" fill="{lang_color}"/>
  <text x="39" y="149" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{t["ink_muted"]}">{escape(lang)}</text>
  <text x="458" y="149" text-anchor="end" font-family="{FONT_MONO}" font-size="11" fill="{acc}">OPEN REPO →</text>

  <!-- Schematic Icon -->
  {schematic_icon(proj["icon"], acc, t["border_hi"])}
</svg>'''


def render_footer(m: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 1200, 82

    # Smooth horizon sine wave
    pts = []
    for i in range(61):
        x = 32 + (i / 60.0) * (w - 64)
        y = 41 + 11 * math.sin(i * 0.32) * math.cos(i * 0.08)
        pts.append((x, y))
    wave_d = smooth_path(pts)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Bahtya Telemetry Footer">
  <defs>
    <linearGradient id="footWave" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["amber"]}" stop-opacity="0.1"/>
      <stop offset="30%" stop-color="{t["amber"]}" stop-opacity="0.65"/>
      <stop offset="70%" stop-color="{t["cyan"]}" stop-opacity="0.65"/>
      <stop offset="100%" stop-color="{t["emerald"]}" stop-opacity="0.1"/>
    </linearGradient>
    <style>
      .foot-dash {{ stroke-dasharray: 12 8; animation: fDash 14s linear infinite; }}
      @keyframes fDash {{ to {{ stroke-dashoffset: -200; }} }}
    </style>
  </defs>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>
  <path d="{wave_d}" fill="none" stroke="url(#footWave)" stroke-width="1.8" class="foot-dash"/>
  <rect x="330" y="21" width="540" height="40" rx="8" fill="{t["panel"]}" stroke="{t["border"]}"/>
  <text x="600" y="39" text-anchor="middle" font-family="{FONT_MONO}" font-size="11.5" font-weight="700" letter-spacing="1.4" fill="{t["ink"]}">BUILD TO UNDERSTAND  ·  DISASSEMBLE TO MASTER</text>
  <text x="600" y="54" text-anchor="middle" font-family="{FONT_MONO}" font-size="9.5" letter-spacing="1" fill="{t["ink_muted"]}">AUTO-SYNCED VIA GITHUB ACTIONS  ·  {escape(m["updated_utc"])}</text>
</svg>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Bahtya GitHub profile SVGs")
    parser.add_argument("--input-json", help="Read GitHub GraphQL JSON from local file instead of calling API")
    parser.add_argument("--out-dir", default="assets", help="Output directory for generated SVGs")
    args = parser.parse_args()

    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8-sig"))
        user = raw["data"]["user"] if "data" in raw else raw
    else:
        token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("ERROR: Set PROFILE_TOKEN / GITHUB_TOKEN or pass --input-json", file=sys.stderr)
            return 1
        user = fetch_github_data(token)

    metrics = compute_metrics(user)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for theme_name in ("dark", "light"):
        (out / f"hero-{theme_name}.svg").write_text(render_hero(metrics, theme_name), encoding="utf-8")
        (out / f"architecture-{theme_name}.svg").write_text(render_architecture(theme_name), encoding="utf-8")
        (out / f"telemetry-{theme_name}.svg").write_text(render_telemetry(metrics, theme_name), encoding="utf-8")
        (out / f"footer-{theme_name}.svg").write_text(render_footer(metrics, theme_name), encoding="utf-8")
        for proj in FLAGSHIP_PROJECTS:
            (out / f"card-{proj['slug']}-{theme_name}.svg").write_text(
                render_project_card(proj, metrics, theme_name), encoding="utf-8"
            )

    print(f"Generated {4 * 2 + len(FLAGSHIP_PROJECTS) * 2} SVGs in {out.resolve()} (contributions={metrics['total_contributions']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
