"""Deterministic, private, offline HTML artifacts for the brain CLI."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import signal
import stat
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import quote


class ArtifactError(RuntimeError):
    """Stable refusal at the local artifact boundary."""


WEBHOOK_RE = re.compile(
    r"(?i)(?:https?://[^\s\"'<>]*(?:hooks?|webhooks?)[^\s\"'<>]*|"
    r"(?:webhook|hook)[_-]?(?:url|token|secret)\s*[:=])"
)
CREDENTIAL_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|client[_-]?secret|secret|token|passwd|password)"
    r"\s*[:=]\s*[\"']?[A-Za-z0-9_+./=-]{8,}"
)
ABSOLUTE_PATH_RE = re.compile(
    r"(?:(?<![A-Za-z0-9._-])/(?!/)[^\s<>()\[\]{}\"']+|"
    r"(?<![A-Za-z0-9._-])[A-Za-z]:[\\/][^\s<>()\[\]{}\"']*|"
    r"\\\\[^\\\s]+\\[^\s<>()\[\]{}\"']*)"
)
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_-]{0,79}$")


def sensitive(api, text: str) -> bool:
    return (
        WEBHOOK_RE.search(text) is not None
        or CREDENTIAL_RE.search(text) is not None
        or any(
        pattern.search(text) for _name, pattern in api.SECRET_RULES
        )
    )


def host_identifiers(root: Path) -> frozenset[str]:
    parts = root.absolute().parts
    values = set()
    for index, part in enumerate(parts[:-1]):
        if part.casefold() in {"home", "users"} and parts[index + 1]:
            values.add(parts[index + 1].casefold())
    return frozenset(values)


def contains_identifier(value: str, identifiers: frozenset[str]) -> bool:
    folded = value.casefold()
    return any(identifier in folded for identifier in identifiers)


def safe_path(
    api, rel: object, *, forbidden: frozenset[str] = frozenset()
) -> bool:
    if not isinstance(rel, str) or not rel or len(rel) > 512:
        return False
    if rel != api.nfc(rel) or rel.startswith(("/", ".")) or "\\" in rel or ":" in rel:
        return False
    parts = rel.split("/")
    return all(
        part not in {"", ".", ".."}
        and all(character >= " " and character != "\x7f" for character in part)
        for part in parts
    ) and not sensitive(api, rel) and not contains_identifier(rel, forbidden)


def safe_text(
    api,
    value: object,
    fallback: str,
    *,
    forbidden: frozenset[str] = frozenset(),
) -> str:
    text = api.nfc(" ".join(str(value if value is not None else "").split()))
    text = "".join(
        character for character in text if character >= " " and character != "\x7f"
    )
    if (
        not text
        or sensitive(api, text)
        or ABSOLUTE_PATH_RE.search(text)
        or contains_identifier(text, forbidden)
    ):
        return fallback
    return text[: api.ARTIFACT_TEXT_LIMIT].rstrip() or fallback


def json_for_html(value: object) -> str:
    text = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def note_href(rel: str) -> str:
    return "../../" + quote(rel, safe="/-._~")


def safe_index(api, root: Path) -> tuple[dict, frozenset[str]]:
    """Build one authenticated, tracked, shared-only derived index."""
    tracked = api.git_tracked(root)
    if tracked is None:
        raise ArtifactError("tracked artifact corpus is unavailable")
    notes, assets = api.walk_corpus(root, selected_environment=None)
    identifiers = host_identifiers(root)
    considered_notes = [
        rel
        for rel in notes
        if rel in tracked
        and not rel.startswith(api.ENVIRONMENTS_RELPATH + "/")
        and not rel.startswith(api.ARTIFACT_DIR_RELPATH + "/")
        and safe_path(api, rel, forbidden=identifiers)
    ]
    considered_assets = [
        rel
        for rel in assets
        if rel in tracked
        and not rel.startswith(api.ENVIRONMENTS_RELPATH + "/")
        and not rel.startswith(api.ARTIFACT_DIR_RELPATH + "/")
        and safe_path(api, rel, forbidden=identifiers)
    ]
    snapshots: dict[str, bytes | None] = {}
    unreadable: set[str] = set()
    secret_bearing: set[str] = set()
    for rel in considered_notes:
        try:
            raw = api._read_nofollow_bytes(root, rel, max_bytes=2 * 1024 * 1024)
        except OSError:
            raw = None
            unreadable.add(rel)
        snapshots[rel] = raw
        if raw is not None and sensitive(api, raw.decode("utf-8", errors="replace")):
            secret_bearing.add(rel)
    index = api.build_index(
        root,
        considered_notes,
        considered_assets,
        note_snapshots=snapshots,
    )
    restricted = {
        rel for rel, record in index["notes"].items() if api.is_restricted(record)
    }
    targeting_restricted = {
        rel
        for rel, record in index["notes"].items()
        if any(
            link.get("resolved") in restricted for link in record.get("links", [])
        )
    }
    excluded = restricted | targeting_restricted | secret_bearing | unreadable
    safe_paths = set(index["notes"]) - excluded
    # Re-resolve only after privacy filtering. The first pass exists solely to
    # classify direct/ambiguous restricted targets; allowing its resolver
    # state into metrics would let a filtered basename/title collision change
    # otherwise safe output.
    safe_snapshots = {rel: snapshots[rel] for rel in sorted(safe_paths)}
    safe = api.build_index(
        root,
        sorted(safe_paths),
        considered_assets,
        note_snapshots=safe_snapshots,
    )
    return {**safe, "assets": []}, identifiers


def artifact_as_of(api, index: dict, explicit: str | None) -> tuple[date, str]:
    if explicit is not None:
        parsed = api.iso_date(explicit)
        if parsed is None or explicit != parsed.isoformat():
            raise ArtifactError("artifact --as-of must be an ISO date")
        return parsed, "explicit"
    candidates = [
        parsed
        for record in index["notes"].values()
        if (parsed := api.iso_date(record.get("updated"))) is not None
    ]
    return (
        max(candidates) if candidates else date(1970, 1, 1),
        "latest-source-updated",
    )


def build_data(api, root: Path, *, as_of: str | None = None) -> dict:
    index, host_ids = safe_index(api, root)
    as_of_date, as_of_source = artifact_as_of(api, index, as_of)
    paths = set(index["notes"])
    raw_edges = sorted(
        {
            (source, link["resolved"])
            for source, record in index["notes"].items()
            for link in record["links"]
            if link.get("resolved") in paths
        }
    )
    degrees = {rel: 0 for rel in paths}
    for source, target in raw_edges:
        degrees[source] += 1
        if source != target:
            degrees[target] += 1
    ranked = sorted(
        paths,
        key=lambda rel: (
            -degrees[rel],
            api.fold(
                safe_text(
                    api,
                    index["notes"][rel].get("title"),
                    rel.rsplit("/", 1)[-1],
                    forbidden=host_ids,
                )
            ),
            rel,
        ),
    )
    selected_paths = set(ranked[: api.ARTIFACT_MAX_NODES])
    ordered_paths = sorted(selected_paths)
    identifiers = {rel: number for number, rel in enumerate(ordered_paths)}
    nodes = []
    all_tags: set[str] = set()
    for rel in ordered_paths:
        record = index["notes"][rel]
        tags = sorted(
            {
                tag
                for tag in api.frontmatter_tags(record)
                if tag != api.RESTRICTED_TAG
                and TAG_RE.fullmatch(tag)
                and not contains_identifier(tag, host_ids)
            }
        )[:12]
        all_tags.update(tags)
        nodes.append(
            {
                "degree": degrees[rel],
                "href": note_href(rel),
                "id": identifiers[rel],
                "path": rel,
                "tags": tags,
                "title": safe_text(
                    api,
                    record.get("title"),
                    rel.rsplit("/", 1)[-1],
                    forbidden=host_ids,
                ),
            }
        )
    all_selected_edges = [
        {"source": identifiers[source], "target": identifiers[target]}
        for source, target in raw_edges
        if source in selected_paths and target in selected_paths
    ]
    selected_edges = all_selected_edges[: api.ARTIFACT_MAX_EDGES]
    report = api.compute_report(
        index,
        as_of_date,
        api.report_thresholds({}),
        None,
    )
    expiry = {"beyondCap": 0, "expired": 0, "missing": 0}
    tasks = {"malformed": 0, "open": 0, "overdue": 0}
    for rel, record in index["notes"].items():
        frontmatter = record["frontmatter"]
        expires = api.iso_date(frontmatter.get("expires"))
        updated = api.iso_date(record.get("updated"))
        if expires is not None:
            expiry["expired"] += int(expires < as_of_date)
            expiry["beyondCap"] += int(
                updated is not None
                and (expires - updated).days > api.EXPIRES_CAP_DAYS
            )
        elif (
            frontmatter
            and "expires" not in frontmatter
            and not api.expires_exempt(rel, frontmatter)
            and not api.is_template(rel)
        ):
            expiry["missing"] += 1
        for task in record["tasks"]:
            if task.get("status") != "open":
                continue
            tasks["open"] += 1
            tasks["malformed"] += int(bool(task.get("malformed")))
            due = api.iso_date(task.get("due"))
            tasks["overdue"] += int(due is not None and due < as_of_date)
    metrics = {
        "edges": len(raw_edges),
        "expired": expiry["expired"],
        "expiresBeyondCap": expiry["beyondCap"],
        "inboxNotes": sum(
            rel.startswith(api.INBOX_PREFIX) and rel != "02_Inbox/README.md"
            for rel in paths
        ),
        "malformedTasks": tasks["malformed"],
        "missingExpires": expiry["missing"],
        "notes": len(paths),
        "openTasks": tasks["open"],
        "orphans": len(report["orphans"]),
        "overdueTasks": tasks["overdue"],
        "staleActive": len(report["staleActive"]),
        "tags": len(all_tags),
        "triageDebt": len(report["inboxAging"]["triageDebt"]),
        "unresolvedLinks": report["unresolvedLinks"]["count"],
    }
    graph = {
        "edges": selected_edges,
        "nodes": nodes,
        "tags": sorted(all_tags),
        "truncatedEdges": max(0, len(all_selected_edges) - len(selected_edges)),
        "truncatedNodes": max(0, len(paths) - len(nodes)),
    }
    source = {
        "asOf": as_of_date.isoformat(),
        "asOfSource": as_of_source,
        "filters": [
            "absolute-path-and-credential-bearing-metadata",
            "generated-artifact-outputs",
            "non-current-environment-content",
            "restricted-notes-and-inbound-sources",
            "unreadable-symlink-and-untracked-content",
        ],
        "generator": api.ARTIFACT_GENERATOR,
        "generatedAt": as_of_date.isoformat() + "T00:00:00Z",
        "scope": "git-tracked-shared-nonrestricted-derived-metadata",
        "schemaVersion": api.ARTIFACT_SCHEMA_VERSION,
    }
    digest_input = {"graph": graph, "health": metrics, "source": source}
    return {
        **digest_input,
        "inputDigest": api._sha256_bytes(api._canonical_json(digest_input)),
    }


def artifact_css() -> str:
    return """
:root{color-scheme:dark light;font-family:ui-sans-serif,system-ui,sans-serif;line-height:1.5;--bg:#0b1220;--panel:#162033;--text:#eef4ff;--muted:#a9b8d0;--accent:#74c0fc;--focus:#ffd43b;--border:#31415c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text)}header,main,footer{max-width:1200px;margin:auto;padding:1rem}header{border-bottom:1px solid var(--border)}h1,h2{line-height:1.2}.lede,.muted{color:var(--muted)}.toolbar{display:flex;flex-wrap:wrap;gap:.75rem;align-items:end;margin:1rem 0}.control{display:grid;gap:.25rem;min-width:12rem}input,select,button{font:inherit;padding:.55rem .7rem;color:var(--text);background:var(--panel);border:1px solid var(--border);border-radius:.4rem}button{cursor:pointer}a{color:var(--accent)}:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(16rem,1fr);gap:1rem}.panel,.metric{background:var(--panel);border:1px solid var(--border);border-radius:.6rem;padding:1rem}.graph{width:100%;min-height:32rem;border:1px solid var(--border);border-radius:.4rem}.edge{stroke:var(--border);stroke-width:1}.node{fill:var(--accent);cursor:pointer}.graph a:focus .node{stroke:var(--focus);stroke-width:4}.node-label{fill:var(--text);font-size:12px;pointer-events:none}.node-list,.static-list{max-height:32rem;overflow:auto;padding-left:1.25rem}.node-list li{margin:.35rem 0}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.75rem}.metric strong{font-size:1.8rem;display:block}.badge{display:inline-block;padding:.15rem .45rem;border:1px solid var(--border);border-radius:999px;color:var(--muted)}.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:760px){.layout{grid-template-columns:1fr}.graph{min-height:24rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
@media(prefers-color-scheme:light){:root{--bg:#f7f9fc;--panel:#fff;--text:#172033;--muted:#50617a;--accent:#075ea8;--focus:#8a5400;--border:#c8d2e1}}
""".strip()


def graph_script() -> str:
    return """
'use strict';
const data=JSON.parse(document.getElementById('artifact-data').textContent);
const svg=document.getElementById('graph');const list=document.getElementById('node-list');const search=document.getElementById('search');const tag=document.getElementById('tag');const count=document.getElementById('visible-count');const NS=svg.namespaceURI;
function clear(element){while(element.firstChild)element.removeChild(element.firstChild)}
function matches(node){const query=search.value.trim().toLocaleLowerCase();return(!query||node.title.toLocaleLowerCase().includes(query)||node.path.toLocaleLowerCase().includes(query))&&(!tag.value||node.tags.includes(tag.value))}
function focusSibling(event){const links=[...list.querySelectorAll('a')];const index=links.indexOf(event.target);let next=index;if(event.key==='ArrowDown')next=Math.min(links.length-1,index+1);else if(event.key==='ArrowUp')next=Math.max(0,index-1);else if(event.key==='Home')next=0;else if(event.key==='End')next=links.length-1;else return;event.preventDefault();if(links[next])links[next].focus()}
function render(){const nodes=data.graph.nodes.filter(matches);const ids=new Set(nodes.map(node=>node.id));const ringSize=64;clear(svg);clear(list);svg.setAttribute('viewBox','0 0 1000 720');const positions=new Map();nodes.forEach((node,index)=>{const ring=Math.floor(index/ringSize),offset=index%ringSize,ringCount=Math.min(ringSize,nodes.length-ring*ringSize),radius=nodes.length===1?0:70+ring*35,angle=(Math.PI*2*offset)/Math.max(1,ringCount)-Math.PI/2;positions.set(node.id,{x:500+Math.cos(angle)*radius,y:360+Math.sin(angle)*radius})});data.graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)).forEach(edge=>{const a=positions.get(edge.source),b=positions.get(edge.target),line=document.createElementNS(NS,'line');line.setAttribute('x1',a.x);line.setAttribute('y1',a.y);line.setAttribute('x2',b.x);line.setAttribute('y2',b.y);line.setAttribute('class','edge');svg.appendChild(line)});nodes.forEach(node=>{const point=positions.get(node.id),anchor=document.createElementNS(NS,'a'),circle=document.createElementNS(NS,'circle'),label=document.createElementNS(NS,'text');anchor.setAttribute('href',node.href);anchor.setAttribute('aria-label',node.title);circle.setAttribute('cx',point.x);circle.setAttribute('cy',point.y);circle.setAttribute('r',String(Math.min(16,6+node.degree)));circle.setAttribute('class','node');anchor.appendChild(circle);if(nodes.length<=80){label.setAttribute('x',point.x+12);label.setAttribute('y',point.y+4);label.setAttribute('class','node-label');label.textContent=node.title.slice(0,28);anchor.appendChild(label)}anchor.addEventListener('keydown',event=>{if(event.key===' '){event.preventDefault();anchor.click()}});svg.appendChild(anchor);const item=document.createElement('li'),link=document.createElement('a');link.setAttribute('href',node.href);link.textContent=node.title+' — '+node.path;link.addEventListener('keydown',focusSibling);item.appendChild(link);list.appendChild(item)});count.textContent=String(nodes.length)}
data.graph.tags.forEach(value=>{const option=document.createElement('option');option.setAttribute('value',value);option.textContent=value;tag.appendChild(option)});search.addEventListener('input',render);tag.addEventListener('change',render);render();
""".strip()


def dashboard_script() -> str:
    return """
'use strict';
const filter=document.getElementById('metric-filter');const cards=[...document.querySelectorAll('[data-group]')];const visible=document.getElementById('metric-count');function render(){let count=0;cards.forEach(card=>{const show=filter.value==='all'||card.getAttribute('data-group')===filter.value;card.hidden=!show;if(show)count+=1});visible.textContent=String(count)}filter.addEventListener('change',render);render();
""".strip()


def csp(css: str, script: str, payload: str) -> str:
    style_hash = base64.b64encode(
        hashlib.sha256(css.encode("utf-8")).digest()
    ).decode("ascii")
    script_hash = base64.b64encode(
        hashlib.sha256(script.encode("utf-8")).digest()
    ).decode("ascii")
    payload_hash = base64.b64encode(
        hashlib.sha256(payload.encode("utf-8")).digest()
    ).decode("ascii")
    return (
        "default-src 'none'; base-uri 'none'; connect-src 'none'; "
        "font-src 'none'; form-action 'none'; frame-ancestors 'none'; "
        "img-src 'none'; object-src 'none'; "
        f"style-src 'sha256-{style_hash}'; "
        f"script-src 'sha256-{payload_hash}' 'sha256-{script_hash}'"
    )


def html_document(
    api, *, title: str, lede: str, body: str, data: dict, script: str
) -> bytes:
    css = artifact_css()
    payload = json_for_html(data)
    policy = csp(css, script, payload)
    provisional = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{html.escape(policy, quote=True)}">\n'
        '<meta name="artifact-content-sha256" content="PENDING">\n'
        f'<title>{html.escape(title)}</title>\n<style>{css}</style>\n</head>\n<body>\n'
        f'{api.ARTIFACT_HTML_MARKER}\n<header><h1>{html.escape(title)}</h1>'
        f'<p class="lede">{html.escape(lede)}</p></header>\n<main>\n{body}\n</main>\n'
        '<footer><p class="muted">Local generated artifact. Hosting and notifications are disabled.</p></footer>\n'
        f'<script type="application/json" id="artifact-data">{payload}</script>\n'
        f'<script>{script}</script>\n</body>\n</html>\n'
    ).encode("utf-8")
    neutral = provisional.replace(b'content="PENDING"', b'content=""', 1)
    digest = api._sha256_bytes(neutral)
    return provisional.replace(
        b'content="PENDING"', f'content="{digest}"'.encode("ascii"), 1
    )


def render_link_graph(api, data: dict) -> bytes:
    nodes = data["graph"]["nodes"]
    static_rows = "".join(
        f'<li><a href="{html.escape(node["href"], quote=True)}">'
        f'{html.escape(node["title"])}</a> '
        f'<span class="muted">{html.escape(node["path"])}</span></li>'
        for node in nodes[: api.ARTIFACT_STATIC_LINK_CAP]
    ) or "<li>No safe tracked notes are available.</li>"
    body = (
        '<section aria-labelledby="summary-heading" class="panel"><h2 id="summary-heading">Static summary</h2>'
        f'<p>{len(nodes)} displayed nodes; {len(data["graph"]["edges"])} displayed edges. '
        f'{data["graph"]["truncatedNodes"]} nodes and {data["graph"]["truncatedEdges"]} edges are outside display caps.</p>'
        '<noscript><p>JavaScript is off. Use the safe note links below.</p></noscript>'
        f'<ol class="static-list">{static_rows}</ol></section>'
        '<section aria-labelledby="explore-heading"><h2 id="explore-heading">Explore</h2>'
        '<div class="toolbar"><label class="control" for="search">Search notes<input id="search" type="search" autocomplete="off"></label>'
        '<label class="control" for="tag">Filter by tag<select id="tag"><option value="">All safe tags</option></select></label>'
        '<p aria-live="polite"><span id="visible-count">0</span> visible notes</p></div>'
        '<div class="layout"><div class="panel"><svg id="graph" class="graph" role="img" aria-label="Deterministic vault link graph"></svg></div>'
        '<div class="panel"><h2>Keyboard note list</h2><p class="muted">Use Tab or arrow keys; Enter opens a note.</p>'
        '<ol id="node-list" class="node-list"></ol></div></div></section>'
    )
    return html_document(
        api,
        title="Vault Link Graph",
        lede="A bounded, deterministic graph of safe tracked note links. No raw note bodies are embedded.",
        body=body,
        data={
            "graph": data["graph"],
            "inputDigest": data["inputDigest"],
            "source": data["source"],
        },
        script=graph_script(),
    )


def render_health_dashboard(api, data: dict) -> bytes:
    labels = {
        "notes": ("Content", "Safe notes"),
        "edges": ("Links", "Resolved note links"),
        "unresolvedLinks": ("Links", "Unresolved links"),
        "orphans": ("Links", "Disconnected notes"),
        "inboxNotes": ("Workflow", "Inbox notes"),
        "triageDebt": ("Workflow", "Inbox triage debt"),
        "openTasks": ("Tasks", "Open tasks"),
        "overdueTasks": ("Tasks", "Overdue tasks"),
        "malformedTasks": ("Tasks", "Malformed task metadata"),
        "staleActive": ("Freshness", "Stale active notes"),
        "expired": ("Freshness", "Expired notes"),
        "missingExpires": ("Freshness", "Missing expiry"),
        "expiresBeyondCap": ("Freshness", "Expiry beyond cap"),
        "tags": ("Content", "Safe tags"),
    }
    cards = "".join(
        f'<article class="metric" data-group="{html.escape(group.casefold())}">'
        f'<span class="badge">{html.escape(group)}</span>'
        f'<strong>{data["health"][key]}</strong><span>{html.escape(label)}</span></article>'
        for key, (group, label) in labels.items()
    )
    body = (
        '<section class="panel" aria-labelledby="snapshot-heading"><h2 id="snapshot-heading">Static health snapshot</h2>'
        f'<p>As of <strong>{html.escape(data["source"]["asOf"])}</strong> '
        f'({html.escape(data["source"]["asOfSource"])}). '
        'Privacy filters are applied before metric derivation.</p>'
        '<noscript><p>JavaScript is off. Every metric remains visible below.</p></noscript></section>'
        '<section aria-labelledby="metrics-heading"><h2 id="metrics-heading">Metrics</h2>'
        '<div class="toolbar"><label class="control" for="metric-filter">Metric group<select id="metric-filter">'
        '<option value="all">All groups</option><option value="content">Content</option>'
        '<option value="links">Links</option><option value="workflow">Workflow</option>'
        '<option value="tasks">Tasks</option><option value="freshness">Freshness</option>'
        '</select></label><p aria-live="polite"><span id="metric-count">0</span> visible metrics</p></div>'
        f'<div class="metrics">{cards}</div></section>'
    )
    return html_document(
        api,
        title="Vault Health Dashboard",
        lede="Derived counts only: no raw note bodies, task text, credentials, environment metadata, or host paths.",
        body=body,
        data={
            "health": data["health"],
            "inputDigest": data["inputDigest"],
            "source": data["source"],
        },
        script=dashboard_script(),
    )


def render_manifest(api, data: dict, html_outputs: dict[str, bytes]) -> bytes:
    payload = {
        "artifacts": [
            {
                "path": rel,
                "sha256": api._sha256_bytes(html_outputs[rel]),
                "sizeBytes": len(html_outputs[rel]),
            }
            for rel in api.ARTIFACT_OUTPUTS[:2]
        ],
        "contentDigest": "",
        "generator": api.ARTIFACT_GENERATOR,
        "inputDigest": data["inputDigest"],
        "owner": "brain-artifacts",
        "schemaVersion": api.ARTIFACT_SCHEMA_VERSION,
        "source": data["source"],
    }
    payload["contentDigest"] = api._sha256_bytes(
        api._canonical_json(payload) + b"\n"
    )
    return api._canonical_json(payload) + b"\n"


def render_all(api, data: dict) -> dict[str, bytes]:
    outputs = {
        api.ARTIFACT_OUTPUTS[0]: render_link_graph(api, data),
        api.ARTIFACT_OUTPUTS[1]: render_health_dashboard(api, data),
    }
    outputs[api.ARTIFACT_OUTPUTS[2]] = render_manifest(api, data, outputs)
    return outputs


def owned(api, rel: str, raw: bytes, mode: int) -> bool:
    if mode != 0o644:
        return False
    if rel.endswith(".html"):
        if api.ARTIFACT_HTML_MARKER.encode("utf-8") not in raw:
            return False
        match = re.search(
            rb'<meta name="artifact-content-sha256" content="([0-9a-f]{64})">',
            raw,
        )
        if match is None:
            return False
        neutral = re.sub(
            rb'<meta name="artifact-content-sha256" content="[0-9a-f]{64}">',
            b'<meta name="artifact-content-sha256" content="">',
            raw,
            count=1,
        )
        return api._sha256_bytes(neutral) == match.group(1).decode("ascii")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return False
    if (
        not isinstance(payload, dict)
        or payload.get("owner") != "brain-artifacts"
        or payload.get("generator") != api.ARTIFACT_GENERATOR
        or payload.get("schemaVersion") != api.ARTIFACT_SCHEMA_VERSION
        or not isinstance(payload.get("contentDigest"), str)
    ):
        return False
    expected = payload["contentDigest"]
    payload["contentDigest"] = ""
    return api._sha256_bytes(api._canonical_json(payload) + b"\n") == expected


def case_collision(api, root: Path, rel: str) -> bool:
    parent_rel, name = rel.rsplit("/", 1)
    parent_path = root / parent_rel
    before = os.lstat(parent_path)
    if api._link_like_stat(before) or not stat.S_ISDIR(before.st_mode):
        raise OSError("artifact parent is unsafe")
    with os.scandir(parent_path) as entries:
        names = sorted(entry.name for entry in entries)
    after = os.lstat(parent_path)
    if (
        api._link_like_stat(after)
        or (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode))
        != (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode))
    ):
        raise OSError("artifact parent changed during read")
    return any(candidate.casefold() == name.casefold() and candidate != name for candidate in names)


def case_collision_at(parent: int, name: str) -> bool:
    """Check a held output parent without resolving its pathname again."""
    return any(
        candidate.casefold() == name.casefold() and candidate != name
        for candidate in os.listdir(parent)
    )


def require_case_clear(item: dict) -> None:
    if case_collision_at(item["parent"], item["name"]):
        raise ArtifactError(
            "artifact output has a case-insensitive collision"
        )


def build_plan(
    api, root: Path, *, as_of: str | None = None
) -> tuple[dict, dict[str, bytes]]:
    data = build_data(api, root, as_of=as_of)
    outputs = render_all(api, data)
    rows = []
    for rel in api.ARTIFACT_OUTPUTS:
        desired = outputs[rel]
        try:
            if case_collision(api, root, rel):
                raise OSError("case collision")
            current, info = api._read_nofollow_file(
                root, rel, max_bytes=8 * 1024 * 1024
            )
            mode = stat.S_IMODE(info.st_mode)
            recognized = owned(api, rel, current, mode)
            status = (
                "unchanged"
                if recognized and current == desired
                else "update"
                if recognized
                else "blocked"
            )
        except FileNotFoundError:
            status = "create"
        except OSError:
            status = "blocked"
        rows.append(
            {
                "path": rel,
                "sha256": api._sha256_bytes(desired),
                "sizeBytes": len(desired),
                "status": status,
            }
        )
    plan = {
        "artifacts": rows,
        "fresh": all(row["status"] == "unchanged" for row in rows),
        "generator": api.ARTIFACT_GENERATOR,
        "inputDigest": data["inputDigest"],
        "schemaVersion": api.ARTIFACT_SCHEMA_VERSION,
        "source": data["source"],
        "summary": {
            "edges": data["health"]["edges"],
            "notes": data["health"]["notes"],
            "outputs": len(rows),
        },
    }
    return plan, outputs


def write(
    api,
    root: Path,
    desired: dict[str, bytes],
    *,
    verify=None,
) -> dict:
    """Caught-interruption transaction over the exact generated inventory."""
    if set(desired) != set(api.ARTIFACT_OUTPUTS):
        raise ArtifactError("artifact output inventory is invalid")
    if not api._migration_mutation_supported():
        raise ArtifactError(
            "safe artifact writes are unavailable; preview/check only"
        )
    prepared: list[dict] = []
    quarantined: list[dict] = []
    applied: list[dict] = []
    previous_term = None
    committed = False
    recovery: list[str] = []
    try:
        for rel in api.ARTIFACT_OUTPUTS:
            parent, name = api._open_migration_parent(root, rel)
            item = {
                "desired": desired[rel],
                "name": name,
                "new": None,
                "parent": parent,
                "rel": rel,
                "source": None,
                "source_info": None,
                "stage_ownership": {},
                "backup": None,
            }
            prepared.append(item)
            require_case_clear(item)
            try:
                source, source_info = api._read_migration_at(parent, name)
            except FileNotFoundError:
                source = source_info = None
            except (OSError, api.LinkMigrationError):
                raise ArtifactError("existing artifact output is unsafe") from None
            if source is not None and not owned(
                api, rel, source, stat.S_IMODE(source_info.st_mode)
            ):
                raise ArtifactError(
                    "existing artifact output is foreign or modified; preserved"
                )
            item["source"], item["source_info"] = source, source_info
            if source == item["desired"]:
                continue
            item["new"] = api._unused_migration_name(parent, name, "new")
            require_case_clear(item)
            api._stage_migration_at(
                parent,
                name,
                item["desired"],
                0o644,
                ownership=item["stage_ownership"],
                reserved_name=item["new"],
            )
            if source is not None:
                item["backup"] = api._unused_migration_name(parent, name, "old")
        changed = [item for item in prepared if item["new"] is not None]

        def reauthenticate_outputs() -> None:
            for item in prepared:
                require_case_clear(item)
                try:
                    actual, actual_info = api._read_migration_at(
                        item["parent"], item["name"]
                    )
                except (FileNotFoundError, OSError, api.LinkMigrationError):
                    raise ArtifactError(
                        "artifact output changed after verification; recovery preserved"
                    ) from None
                if (
                    actual != item["desired"]
                    or stat.S_IMODE(actual_info.st_mode) != 0o644
                ):
                    raise ArtifactError(
                        "artifact output changed after verification; recovery preserved"
                    )
                if item["new"] is not None:
                    try:
                        staged_info = os.stat(
                            item["new"],
                            dir_fd=item["parent"],
                            follow_symlinks=False,
                        )
                    except OSError:
                        raise ArtifactError(
                            "artifact output changed after verification; recovery preserved"
                        ) from None
                    if (
                        api._link_migration_identity(actual_info)
                        != item["stage_ownership"].get("identity")
                        or (actual_info.st_dev, actual_info.st_ino)
                        != (staged_info.st_dev, staged_info.st_ino)
                    ):
                        raise ArtifactError(
                            "artifact output changed after verification; recovery preserved"
                        )
                elif (
                    item["source_info"] is None
                    or api._link_migration_identity(actual_info)
                    != api._link_migration_identity(item["source_info"])
                ):
                    raise ArtifactError(
                        "artifact output changed after verification; recovery preserved"
                    )

        if not changed:
            if verify is not None:
                verify()
            reauthenticate_outputs()
            return {"filesChanged": 0, "status": "unchanged"}
        if hasattr(signal, "SIGTERM"):
            try:
                previous_term = signal.getsignal(signal.SIGTERM)
                signal.signal(
                    signal.SIGTERM,
                    lambda _signal, _frame: (_ for _ in ()).throw(
                        KeyboardInterrupt()
                    ),
                )
            except (ValueError, OSError):
                previous_term = None
        for item in changed:
            require_case_clear(item)
            try:
                current, info = api._read_migration_at(
                    item["parent"], item["name"]
                )
            except FileNotFoundError:
                current = info = None
            if item["source"] is None:
                if current is not None:
                    raise ArtifactError(
                        "artifact output appeared before publication; preserved"
                    )
            elif (
                current != item["source"]
                or api._link_migration_identity(info)
                != api._link_migration_identity(item["source_info"])
            ):
                raise ArtifactError(
                    "artifact output changed before replacement; preserved"
                )
            if item["backup"] is not None:
                # Register rollback intent before the first mutating call. A
                # caught interrupt may arrive after rename/fsync returns but
                # before Python executes the next statement.
                quarantined.append(item)
                api._quarantine_migration_at(
                    item["parent"], item["name"], item["backup"]
                )
                # The final-component check and rename cannot be one portable
                # syscall. Authenticate the object after quarantine and put a
                # raced occupant straight back before publishing anything.
                backup, backup_info = api._read_migration_at(
                    item["parent"], item["backup"]
                )
                if (
                    backup != item["source"]
                    or api._link_migration_identity(backup_info)
                    != api._link_migration_identity(item["source_info"])
                ):
                    if api._restore_quarantined_at(
                        item["parent"], item["backup"], item["name"]
                    ):
                        os.unlink(item["backup"], dir_fd=item["parent"])
                        os.fsync(item["parent"])
                        item["backup"] = None
                        quarantined.pop()
                    raise ArtifactError(
                        "artifact output changed before quarantine; preserved"
                    )
        for item in changed:
            require_case_clear(item)
            applied.append(item)
            staged, staged_info = api._read_migration_at(
                item["parent"], item["new"]
            )
            if (
                staged != item["desired"]
                or api._link_migration_identity(staged_info)
                != item["stage_ownership"].get("identity")
            ):
                raise ArtifactError(
                    "artifact stage changed before publication; preserved"
                )
            api._install_migration_at(
                item["parent"], item["new"], item["name"]
            )
        for item in changed:
            actual, actual_info = api._read_migration_at(
                item["parent"], item["name"]
            )
            staged_info = os.stat(
                item["new"], dir_fd=item["parent"], follow_symlinks=False
            )
            if (
                actual != item["desired"]
                or stat.S_IMODE(actual_info.st_mode) != 0o644
                or (actual_info.st_dev, actual_info.st_ino)
                != (staged_info.st_dev, staged_info.st_ino)
            ):
                raise ArtifactError(
                    "artifact output changed during publication; recovery preserved"
                )
        for item in prepared:
            require_case_clear(item)
        if verify is not None:
            verify()
        reauthenticate_outputs()
        committed = True
        return {"filesChanged": len(changed), "status": "written"}
    except BaseException as exc:
        if not committed:
            for item in reversed(applied):
                try:
                    actual, info = api._read_migration_at(
                        item["parent"], item["name"]
                    )
                    stage = os.stat(
                        item["new"],
                        dir_fd=item["parent"],
                        follow_symlinks=False,
                    )
                    if (
                        (info.st_dev, info.st_ino)
                        == (stage.st_dev, stage.st_ino)
                    ):
                        os.unlink(item["name"], dir_fd=item["parent"])
                except (FileNotFoundError, OSError, api.LinkMigrationError):
                    pass
            for item in reversed(quarantined):
                try:
                    try:
                        backup, backup_info = api._read_migration_at(
                            item["parent"], item["backup"]
                        )
                    except FileNotFoundError:
                        # The interrupt may have preceded the rename. Accept
                        # only the exact still-present original in that case.
                        current, current_info = api._read_migration_at(
                            item["parent"], item["name"]
                        )
                        if (
                            current != item["source"]
                            or api._link_migration_identity(current_info)
                            != api._link_migration_identity(item["source_info"])
                        ):
                            recovery.append(item["rel"])
                        continue
                    if (
                        backup != item["source"]
                        or api._link_migration_identity(backup_info)
                        != api._link_migration_identity(item["source_info"])
                    ):
                        recovery.append(
                            f'{item["rel"]}::{item["backup"]}'
                        )
                        continue
                    if not api._restore_quarantined_at(
                        item["parent"], item["backup"], item["name"]
                    ):
                        recovery.append(
                            f'{item["rel"]}::{item["backup"]}'
                        )
                    else:
                        os.unlink(item["backup"], dir_fd=item["parent"])
                        item["backup"] = None
                except (OSError, api.LinkMigrationError):
                    recovery.append(f'{item["rel"]}::{item["backup"]}')
        if recovery:
            raise ArtifactError(
                "artifact transaction needs recovery from "
                + ", ".join(recovery)
            ) from None
        if isinstance(exc, (ArtifactError, KeyboardInterrupt)):
            raise
        raise ArtifactError(
            "artifact transaction failed; prior outputs preserved"
        ) from None
    finally:
        active_error = sys.exc_info()[0] is not None
        cleanup_error = None
        if previous_term is not None:
            try:
                signal.signal(signal.SIGTERM, previous_term)
            except (ValueError, OSError):
                cleanup_error = ArtifactError(
                    "artifact signal cleanup failed safely"
                )
        for item in prepared:
            try:
                if item["new"] is not None:
                    api._remove_owned_migration_stage(item)
                if committed and item["backup"] is not None:
                    require_case_clear(item)
                    current, info = api._read_migration_at(
                        item["parent"], item["name"]
                    )
                    if (
                        current != item["desired"]
                        or stat.S_IMODE(info.st_mode) != 0o644
                    ):
                        raise ArtifactError(
                            "artifact changed before backup retirement; "
                            "recovery preserved"
                        )
                    backup, backup_info = api._read_migration_at(
                        item["parent"], item["backup"]
                    )
                    if (
                        backup != item["source"]
                        or api._link_migration_identity(backup_info)
                        != api._link_migration_identity(item["source_info"])
                    ):
                        raise ArtifactError(
                            "artifact backup ownership changed; preserved"
                        )
                    os.unlink(item["backup"], dir_fd=item["parent"])
                    os.fsync(item["parent"])
            except (OSError, api.LinkMigrationError, ArtifactError) as exc:
                cleanup_error = cleanup_error or ArtifactError(str(exc))
            finally:
                try:
                    os.close(item["parent"])
                except OSError:
                    pass
        if cleanup_error is not None and not active_error:
            raise cleanup_error


def open_local(api, root: Path, *, opener=None) -> int:
    if opener is None:
        import webbrowser

        opener = webbrowser.open_new_tab
    snapshots = []
    for rel in api.ARTIFACT_OUTPUTS[:2]:
        try:
            if case_collision(api, root, rel):
                raise OSError("case collision")
            raw, info = api._read_nofollow_file(
                root, rel, max_bytes=8 * 1024 * 1024
            )
        except OSError:
            raise ArtifactError("local artifact open refused") from None
        if not owned(api, rel, raw, stat.S_IMODE(info.st_mode)):
            raise ArtifactError("local artifact open refused")
        snapshots.append((rel, raw))
    opened = 0
    try:
        with tempfile.TemporaryDirectory(
            prefix="brain-artifact-open-"
        ) as temporary:
            snapshot_root = Path(temporary)
            snapshot_paths = []
            for rel, raw in snapshots:
                name = rel.rsplit("/", 1)[-1]
                target = snapshot_root / name
                descriptor = os.open(
                    target,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o400,
                )
                try:
                    offset = 0
                    while offset < len(raw):
                        offset += os.write(descriptor, raw[offset:])
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                copied, copied_info = api._read_nofollow_file(
                    snapshot_root, name, max_bytes=8 * 1024 * 1024
                )
                if copied != raw or stat.S_IMODE(copied_info.st_mode) != 0o400:
                    raise ArtifactError("local artifact snapshot refused")
                snapshot_paths.append(target)
            for target in snapshot_paths:
                try:
                    accepted = opener(target.absolute().as_uri())
                except Exception:
                    raise ArtifactError("local browser declined an artifact") from None
                if not accepted:
                    raise ArtifactError("local browser declined an artifact")
                opened += 1
    except OSError:
        raise ArtifactError("local artifact snapshot refused") from None
    return opened


def command(api, root: Path, args) -> int:
    try:
        plan, outputs = build_plan(api, root, as_of=args.as_of)
        if any(row["status"] == "blocked" for row in plan["artifacts"]):
            raise ArtifactError("artifact output ownership check failed")
        result = None
        if args.write:
            refreshed: dict[str, object] = {}

            def require_fresh_write() -> None:
                current_plan, current_outputs = build_plan(
                    api, root, as_of=args.as_of
                )
                if not current_plan["fresh"]:
                    raise ArtifactError(
                        "artifact outputs changed after publication; preserved"
                    )
                refreshed["plan"] = current_plan
                refreshed["outputs"] = current_outputs

            result = write(
                api,
                root,
                outputs,
                verify=require_fresh_write,
            )
            plan = refreshed["plan"]
            outputs = refreshed["outputs"]
        opened = 0
        if args.open:
            if not plan["fresh"]:
                raise ArtifactError(
                    "artifacts must be fresh before local open"
                )
            opened = open_local(api, root)
    except (ArtifactError, KeyboardInterrupt):
        message = "artifact generation failed safely"
        if args.json:
            print(json.dumps({"error": message}, indent=1, sort_keys=True))
        else:
            print(f"error: {message}", file=sys.stderr)
        return 1
    payload = {**plan, "opened": opened, "write": result}
    if args.json:
        print(
            json.dumps(
                payload, ensure_ascii=False, indent=1, sort_keys=True
            )
        )
    else:
        statuses = ", ".join(
            f'{row["path"]}: {row["status"]}' for row in plan["artifacts"]
        )
        print(
            ("artifacts: fresh; " if plan["fresh"] else "artifact preview: ")
            + statuses
        )
        if result is not None:
            print(f'written: {result["filesChanged"]} files')
        if opened:
            print(f"opened: {opened} local artifacts")
    return 1 if args.check and not plan["fresh"] else 0
