"""Human-readable Markdown & actionable remediation formatter for QA audit reports."""

from __future__ import annotations

from typing import Any


def format_audit_markdown(report: dict[str, Any]) -> str:
    """Render an audit_image or audit_animation dict into a concise Markdown checklist."""
    status = str(report.get("status", "unknown")).upper()
    badge = {"PASS": "🟢 PASS", "WARN": "🟡 WARN", "FAIL": "🔴 FAIL"}.get(status, status)
    lines = [
        f"# Pixel Forge QA Report — {badge}",
        f"- **Preset:** `{report.get('preset', 'unknown')}`",
    ]

    if "frame_count" in report:
        lines.append(f"- **Frames:** {report['frame_count']} (uniform size: `{report.get('uniform_size')}`)")
        lines.append(f"- **Mean Frame Delta:** `{report.get('mean_delta_ratio', 0.0):.4f}`")
        lines.append(f"- **Static Zone Drift:** `{report.get('static_zone_drift_pixels', 0)}` px")
    else:
        lines.append(f"- **Canvas Size:** `{report.get('size')}`")
        lines.append("\n## Tier 1 — Universal Hard Gates")
        for key, res in (report.get("tier1_hard") or {}).items():
            mark = "✅" if res.get("passed") else "❌"
            lines.append(f"- {mark} **{key}**: `{res}`")
        if report.get("tier2_style"):
            lines.append("\n## Tier 2 — Style & Perspective Gates")
            for key, res in report["tier2_style"].items():
                mark = "✅" if res.get("passed") else "⚠️"
                lines.append(f"- {mark} **{key}**: `{res}`")

    if report.get("warnings"):
        lines.append("\n## Warnings")
        for w in report["warnings"]:
            lines.append(f"- ⚠️ {w}")

    return "\n".join(lines) + "\n"
