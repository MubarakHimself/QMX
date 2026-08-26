"""Pure HTML/markdown rendering of a stored CT-32 artifact (Story 19.5).

Renderers are field/token substitution only. They add no computation and
derive no new number. The headline shows ``world`` and the account-binding
role verbatim and unmissably. HTML and markdown are display derivatives,
AD-10-excluded from identity, written into the run's own output directory.
There is no shared mutable render state (R-RPT-21, R-RPT-24, B-10).
"""

from __future__ import annotations

import html
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import invalid, policy, storage
from qmb.results.ct32 import (
    CT32_ARTIFACT_NAME,
    RESULTS_DIR_NAME,
    as_ct32_artifact,
)

__all__ = [
    "AGENTS_PARSE_HTML",
    "DOWNSTREAM_PUBLISH_ONLY",
    "HTML_REPORT_NAME",
    "HTML_REPORT_RELATIVE_PATH",
    "HTML_TEMPLATE",
    "MARKDOWN_REPORT_NAME",
    "MARKDOWN_REPORT_RELATIVE_PATH",
    "MARKDOWN_TEMPLATE",
    "RENDER_ADDS_COMPUTATION",
    "RENDER_MODE",
    "SHARED_MUTABLE_RENDER_STATE",
    "TOKEN_PATTERN",
    "RenderedReport",
    "RenderedReportPaths",
    "downstream_read_identity",
    "render_html",
    "render_markdown",
    "render_report",
    "render_tokens",
    "substitute_tokens",
    "write_run_renders",
]

RENDER_MODE: Final[str] = "token-substitution"
RENDER_ADDS_COMPUTATION: Final[bool] = False
SHARED_MUTABLE_RENDER_STATE: Final[bool] = False
AGENTS_PARSE_HTML: Final[bool] = False
DOWNSTREAM_PUBLISH_ONLY: Final[bool] = True
HTML_REPORT_NAME: Final[str] = "report.html"
MARKDOWN_REPORT_NAME: Final[str] = "report.md"
HTML_REPORT_RELATIVE_PATH: Final[str] = f"{RESULTS_DIR_NAME}/{HTML_REPORT_NAME}"
MARKDOWN_REPORT_RELATIVE_PATH: Final[str] = f"{RESULTS_DIR_NAME}/{MARKDOWN_REPORT_NAME}"
TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{\{\$([A-Z][A-Z0-9_]*)\}\}")

# CSS uses named sizes only so a digit-scan of the HTML cannot find a number
# the renderer invented. Every digit in a completed report comes from the
# stored CT-32 artifact.
HTML_TEMPLATE: Final[str] = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>CT-32 world={{$WORLD}} account-binding-role={{$ACCOUNT_BINDING_ROLE}}</title>
<style>
.qmb-headline-unmissable {
  font-size: xx-large; font-weight: bold; padding: 1em;
  border-style: solid; border-width: thick;
}
.qmb-world, .qmb-account-binding-role { display: block; }
</style>
</head>
<body>
<header class="qmb-headline qmb-headline-unmissable"
  data-world="{{$WORLD}}"
  data-account-binding-role="{{$ACCOUNT_BINDING_ROLE}}">
<p class="qmb-world">world={{$WORLD}}</p>
<p class="qmb-account-binding-role">account-binding-role={{$ACCOUNT_BINDING_ROLE}}</p>
</header>
<main>
<p>class={{$CLASS}}</p>
<p>evidence_class={{$EVIDENCE_CLASS}}</p>
<p>format_version={{$FORMAT_VERSION}}</p>
<pre class="result_label">{{$RESULT_LABEL}}</pre>
<pre class="population">{{$POPULATION}}</pre>
<pre class="period">{{$PERIOD}}</pre>
<pre class="measure_set">{{$MEASURE_SET}}</pre>
<pre class="suppression_accounting">{{$SUPPRESSION_ACCOUNTING}}</pre>
<pre class="veto_accounting">{{$VETO_ACCOUNTING}}</pre>
</main>
</body>
</html>
"""

MARKDOWN_TEMPLATE: Final[str] = """\
# world={{$WORLD}} · account-binding-role={{$ACCOUNT_BINDING_ROLE}}

class={{$CLASS}}
evidence_class={{$EVIDENCE_CLASS}}
format_version={{$FORMAT_VERSION}}

## result_label

```json
{{$RESULT_LABEL}}
```

## population

```json
{{$POPULATION}}
```

## period

```json
{{$PERIOD}}
```

## measure_set

```json
{{$MEASURE_SET}}
```

## suppression_accounting

```json
{{$SUPPRESSION_ACCOUNTING}}
```

## veto_accounting

```json
{{$VETO_ACCOUNTING}}
```
"""

_JSON_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("RESULT_LABEL", "result_label"),
    ("POPULATION", "population"),
    ("PERIOD", "period"),
    ("MEASURE_SET", "measure_set"),
    ("SUPPRESSION_ACCOUNTING", "suppression_accounting"),
    ("VETO_ACCOUNTING", "veto_accounting"),
)


@dataclass(frozen=True, slots=True)
class RenderedReport:
    """HTML and markdown produced by token substitution of one CT-32 artifact."""

    html: str
    markdown: str
    world: str
    account_binding_role: str
    tokens: Mapping[str, str]
    publish_only: bool = True
    render_adds_computation: bool = False


@dataclass(frozen=True, slots=True)
class RenderedReportPaths:
    """Per-run isolated paths of the display derivatives. Not identity."""

    html: Path
    markdown: Path
    output_dir: Path
    publish_only: bool = True


def downstream_read_identity() -> dict[str, object]:
    """Identity-bearing downstream-read fields. Package SemVer is omitted."""
    return {
        "agents_parse_html": AGENTS_PARSE_HTML,
        "html_payload": False,
        "html_report": HTML_REPORT_RELATIVE_PATH,
        "interpretation_source": "ct-32",
        "markdown_report": MARKDOWN_REPORT_RELATIVE_PATH,
        "publish_only": DOWNSTREAM_PUBLISH_ONLY,
        "render_adds_computation": RENDER_ADDS_COMPUTATION,
        "render_mode": RENDER_MODE,
        "shared_mutable_render_state": SHARED_MUTABLE_RENDER_STATE,
        "targets": ("html", "markdown"),
    }


def render_tokens(source: object) -> Result[dict[str, str]]:
    """Flatten a stored CT-32 artifact into ``{{$KEY}}`` substitution tokens.

    Values are the stored fields stringified. No arithmetic, no derived metric.
    """
    body = as_ct32_artifact(source)
    if is_refusal(body):
        return body
    payload = body.value
    label = payload["result_label"]
    if not isinstance(label, Mapping):
        return invalid(
            "result_label",
            "the stored CT-32 result_label is a mapping the renderer substitutes",
            given=repr(type(label).__name__),
        )
    label_body = cast("Mapping[str, object]", label)
    world = _verbatim_token(label_body.get("world"), "world")
    if is_refusal(world):
        return world
    role = _verbatim_token(payload.get("account_binding_role"), "account_binding_role")
    if is_refusal(role):
        return role
    evidence = _verbatim_token(label_body.get("evidence_class"), "evidence_class")
    if is_refusal(evidence):
        return evidence
    tokens: dict[str, str] = {
        "ACCOUNT_BINDING_ROLE": role.value,
        "CLASS": _json_scalar(payload.get("class", "performance-result")),
        "EVIDENCE_CLASS": evidence.value,
        "FORMAT_VERSION": _json_scalar(payload.get("format_version")),
        "WORLD": world.value,
    }
    for token, field in _JSON_FIELDS:
        dumped = _json_token(payload.get(field), field)
        if is_refusal(dumped):
            return dumped
        tokens[token] = dumped.value
    return Ok(tokens)


def substitute_tokens(template: object, tokens: object) -> Result[str]:
    """Replace ``{{$KEY}}`` markers. Unknown or missing keys are a typed refusal."""
    if not isinstance(template, str) or template.strip() == "":
        return invalid(
            "template",
            "a renderer template is a non-empty string of {{$KEY}} markers",
            given=repr(type(template).__name__),
        )
    if not isinstance(tokens, Mapping):
        return invalid(
            "tokens",
            "token substitution reads a mapping of stored field strings",
            given=repr(type(tokens).__name__),
        )
    table = cast("Mapping[str, object]", tokens)
    missing: list[str] = []
    unknown: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in table:
            missing.append(key)
            return match.group(0)
        value = table[key]
        if not isinstance(value, str):
            unknown.append(key)
            return match.group(0)
        return value

    rendered = TOKEN_PATTERN.sub(_replace, template)
    if missing:
        return invalid(
            "tokens",
            "every {{$KEY}} in the template is substituted from the stored artifact",
            missing=missing,
        )
    if unknown:
        return invalid(
            "tokens",
            "every substitution token is a stored string; the renderer derives no value",
            unknown=unknown,
        )
    leftover = TOKEN_PATTERN.search(rendered)
    if leftover is not None:
        return invalid(
            "tokens",
            "token substitution must leave no unsubstituted {{$KEY}} marker",
            leftover=leftover.group(0),
        )
    return Ok(rendered)


def render_html(source: object) -> Result[str]:
    """Operator-shareable HTML: token substitution of the stored CT-32 artifact."""
    tokens = render_tokens(source)
    if is_refusal(tokens):
        return tokens
    escaped = {key: html.escape(value, quote=True) for key, value in tokens.value.items()}
    return substitute_tokens(HTML_TEMPLATE, escaped)


def render_markdown(source: object) -> Result[str]:
    """Agent-consumable, diffable markdown: token substitution of stored fields."""
    tokens = render_tokens(source)
    if is_refusal(tokens):
        return tokens
    return substitute_tokens(MARKDOWN_TEMPLATE, tokens.value)


def render_report(source: object) -> Result[RenderedReport]:
    """HTML plus markdown of one stored CT-32 artifact. Publish-only."""
    tokens = render_tokens(source)
    if is_refusal(tokens):
        return tokens
    escaped = {key: html.escape(value, quote=True) for key, value in tokens.value.items()}
    html_page = substitute_tokens(HTML_TEMPLATE, escaped)
    if is_refusal(html_page):
        return html_page
    markdown = substitute_tokens(MARKDOWN_TEMPLATE, tokens.value)
    if is_refusal(markdown):
        return markdown
    return Ok(
        RenderedReport(
            html=html_page.value,
            markdown=markdown.value,
            world=tokens.value["WORLD"],
            account_binding_role=tokens.value["ACCOUNT_BINDING_ROLE"],
            tokens=tokens.value,
        )
    )


def write_run_renders(output_dir: object, source: object = None) -> Result[RenderedReportPaths]:
    """Write HTML and markdown into this run's output directory only (R-RPT-24).

    No shared mutable state. Concurrent callers must pass distinct output
    directories. Display files never enter CT-32 identity.
    """
    artifact = output_dir if source is None else source
    rendered = render_report(artifact)
    if is_refusal(rendered):
        return rendered
    root = _as_existing_output_dir(output_dir)
    if is_refusal(root):
        return root
    html_path = root.value / RESULTS_DIR_NAME / HTML_REPORT_NAME
    md_path = root.value / RESULTS_DIR_NAME / MARKDOWN_REPORT_NAME
    written_html = _write_render_bytes(root.value, html_path, rendered.value.html.encode("utf-8"))
    if is_refusal(written_html):
        return written_html
    written_md = _write_render_bytes(root.value, md_path, rendered.value.markdown.encode("utf-8"))
    if is_refusal(written_md):
        return written_md
    return Ok(RenderedReportPaths(html=html_path, markdown=md_path, output_dir=root.value))


def _verbatim_token(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid(
            field,
            "the headline shows the stored world and account-binding role "
            "verbatim; a missing label is not invented (R-RPT-2, R-RPT-19)",
            given=repr(value),
        )
    return Ok(value)


def _json_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_token(value: object, field: str) -> Result[str]:
    if value is None:
        return invalid(
            field,
            "a CT-32 field the renderer substitutes is present on the stored artifact",
        )
    try:
        dumped = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        return invalid(
            field,
            "a stored CT-32 field is JSON-serializable as written; the renderer "
            "does not recompute it",
            given=type(exc).__name__,
        )
    return Ok(dumped)


def _as_existing_output_dir(value: object) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "output_dir",
            "render writes into an existing isolated run output directory",
            given=repr(type(value).__name__),
        )
    if root.is_symlink() or not root.is_dir():
        return storage(
            "output_dir",
            "render writes HTML and markdown into an existing run output directory",
            path=str(root),
        )
    return Ok(root)


def _write_render_bytes(root: Path, target: Path, data: bytes) -> Result[None]:
    """Contained write of a display derivative. Overwrite is allowed; CT-32 is not."""
    if target.name == CT32_ARTIFACT_NAME:
        return policy(
            "ct32_artifact",
            "HTML/markdown rendering never overwrites the stored CT-32 artifact",
            path=str(target),
        )
    results_dir = target.parent
    if results_dir.is_symlink():
        return storage(
            "render_output",
            "refusing to follow a symlink for the run results directory",
            path=str(results_dir),
        )
    try:
        results_dir.mkdir(parents=False, exist_ok=True)
    except OSError as exc:
        return storage(
            "render_output",
            "could not create the run results directory for HTML/markdown",
            given=type(exc).__name__,
            path=str(results_dir),
        )
    try:
        resolved = Path(os.path.realpath(target))
        root_real = Path(os.path.realpath(root))
    except OSError as exc:
        return storage(
            "render_output",
            "could not resolve the render path inside the run directory",
            given=type(exc).__name__,
            path=str(target),
        )
    if target.is_symlink() or not resolved.is_relative_to(root_real):
        return storage(
            "render_output",
            "refusing to follow a symlink or a path that resolves outside the run output directory",
            path=str(target),
            root=str(root),
        )
    flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(  # skylos: ignore[SKY-D215] contained truncate write
            target,
            flags,
            0o600,
        )
    except OSError as exc:
        return storage(
            "render_output",
            "write of the HTML/markdown display derivative failed",
            given=type(exc).__name__,
            path=str(target),
        )
    try:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
        os.fsync(fd)
    except OSError as exc:
        os.close(fd)
        return storage(
            "render_output",
            "write of the HTML/markdown display derivative failed",
            given=type(exc).__name__,
            path=str(target),
        )
    os.close(fd)
    return Ok(None)
