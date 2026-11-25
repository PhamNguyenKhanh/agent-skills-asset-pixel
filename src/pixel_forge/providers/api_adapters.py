"""HTTP API adapters for Gemini, OpenAI, OpenRouter, xAI, and fal.ai (via httpx)."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

import httpx

from pixel_forge.core.image_io import sha256_file
from pixel_forge.providers.base import MediaRequest, MediaResult, ProviderCapabilities, ProviderError
from pixel_forge.providers.config import get_api_key

API_CAPABILITIES: dict[tuple[str, str], ProviderCapabilities] = {
    ("gemini", "image"): ProviderCapabilities(
        name="gemini",
        family="api",
        kind="image",
        default_model="gemini-2.5-flash-image",
        max_references=14,
        supports_transparent=False,
        estimate_usd=0.039,
        env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ),
    ("openai", "image"): ProviderCapabilities(
        name="openai",
        family="api",
        kind="image",
        default_model="gpt-image-1",
        max_references=16,
        supports_transparent=True,
        estimate_usd=0.04,
        env_vars=("OPENAI_API_KEY",),
    ),
    ("openrouter", "image"): ProviderCapabilities(
        name="openrouter",
        family="api",
        kind="image",
        default_model="openai/gpt-image-1",
        max_references=8,
        supports_transparent=False,
        estimate_usd=0.04,
        env_vars=("OPENROUTER_API_KEY",),
    ),
    ("xai", "image"): ProviderCapabilities(
        name="xai",
        family="api",
        kind="image",
        default_model="grok-imagine-image",
        max_references=5,
        supports_transparent=False,
        estimate_usd=0.03,
        env_vars=("XAI_API_KEY",),
    ),
    ("xai", "video"): ProviderCapabilities(
        name="xai",
        family="api",
        kind="video",
        default_model="grok-imagine-video",
        max_references=4,
        supports_last_frame=True,
        estimate_usd=0.30,
        env_vars=("XAI_API_KEY",),
    ),
    ("fal", "image"): ProviderCapabilities(
        name="fal",
        family="api",
        kind="image",
        default_model="fal-ai/flux/dev",
        max_references=4,
        supports_transparent=False,
        estimate_usd=0.03,
        env_vars=("FAL_KEY",),
    ),
    ("fal", "video"): ProviderCapabilities(
        name="fal",
        family="api",
        kind="video",
        default_model="fal-ai/kling-video/v2/master/image-to-video",
        max_references=2,
        supports_last_frame=True,
        estimate_usd=0.40,
        env_vars=("FAL_KEY",),
    ),
}


def _b64_image(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/webp" if suffix == ".webp" else "image/png"
    return mime, base64.b64encode(path.read_bytes()).decode("ascii")


def _data_uri(path: Path) -> str:
    mime, b64 = _b64_image(path)
    return f"data:{mime};base64,{b64}"


def _classify_http_error(resp: httpx.Response, provider: str) -> ProviderError:
    status = resp.status_code
    snippet = resp.text[:240].replace("\n", " ")
    if status in (401, 403):
        return ProviderError(f"{provider}: authentication/entitlement rejected ({status})", code="auth", retryable_next_route=True)
    if status == 402:
        return ProviderError(f"{provider}: insufficient quota/credit (402)", code="quota", retryable_next_route=True)
    if status == 429:
        return ProviderError(f"{provider}: rate limited (429)", code="rate_limit", retryable_next_route=True)
    return ProviderError(f"{provider}: HTTP {status}: {snippet}", code="http_error", retryable_next_route=False)


def _save_bytes(out_dir: Path, filename: str, raw: bytes) -> tuple[Path, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / filename
    target.write_bytes(raw)
    return target, sha256_file(target)


def call_gemini_image(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("gemini")
    if not key:
        raise ProviderError("gemini: GEMINI_API_KEY not configured", code="no_key", retryable_next_route=True)
    parts: list[dict[str, Any]] = [{"text": req.prompt}]
    for ref in req.references:
        mime, b64 = _b64_image(ref)
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, params={"key": key}, json=payload)
    except httpx.HTTPError as exc:
        raise ProviderError(f"gemini: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    if resp.status_code >= 400:
        raise _classify_http_error(resp, "gemini")
    data = resp.json()
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                raw = base64.b64decode(inline["data"])
                out_path, digest = _save_bytes(req.out_dir, "generated.png", raw)
                return MediaResult(status="ok", route="api:gemini", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)
    raise ProviderError("gemini: response contained no image payload", code="empty_response")


def call_openai_image(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("openai")
    if not key:
        raise ProviderError("openai: OPENAI_API_KEY not configured", code="no_key", retryable_next_route=True)
    headers = {"Authorization": f"Bearer {key}"}
    try:
        with httpx.Client(timeout=120.0) as client:
            if req.references:
                files = [("image[]", (p.name, p.read_bytes(), "image/png")) for p in req.references]
                form = {"model": model, "prompt": req.prompt, "size": req.size}
                if req.transparent:
                    form["background"] = "transparent"
                resp = client.post("https://api.openai.com/v1/images/edits", headers=headers, data=form, files=files)
            else:
                body: dict[str, Any] = {"model": model, "prompt": req.prompt, "size": req.size}
                if req.transparent:
                    body["background"] = "transparent"
                resp = client.post("https://api.openai.com/v1/images/generations", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ProviderError(f"openai: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    if resp.status_code >= 400:
        raise _classify_http_error(resp, "openai")
    item = (resp.json().get("data") or [{}])[0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        raw = httpx.get(item["url"], timeout=60.0).content
    else:
        raise ProviderError("openai: response contained neither b64_json nor url", code="empty_response")
    out_path, digest = _save_bytes(req.out_dir, "generated.png", raw)
    return MediaResult(status="ok", route="api:openai", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)


def call_openrouter_image(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("openrouter")
    if not key:
        raise ProviderError("openrouter: OPENROUTER_API_KEY not configured", code="no_key", retryable_next_route=True)
    content: list[dict[str, Any]] = [{"type": "text", "text": req.prompt}]
    for ref in req.references:
        content.append({"type": "image_url", "image_url": {"url": _data_uri(ref)}})
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ProviderError(f"openrouter: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    if resp.status_code >= 400:
        raise _classify_http_error(resp, "openrouter")
    data = resp.json()
    msg = ((data.get("choices") or [{}])[0]).get("message") or {}
    images = msg.get("images") or []
    for entry in images:
        url = (entry.get("image_url") or {}).get("url") or entry.get("url")
        if url and url.startswith("data:"):
            raw = base64.b64decode(url.split(",", 1)[1])
            out_path, digest = _save_bytes(req.out_dir, "generated.png", raw)
            return MediaResult(status="ok", route="api:openrouter", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)
        if url and url.startswith("http"):
            raw = httpx.get(url, timeout=60.0).content
            out_path, digest = _save_bytes(req.out_dir, "generated.png", raw)
            return MediaResult(status="ok", route="api:openrouter", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)
    raise ProviderError("openrouter: response contained no generated image", code="empty_response")


def call_xai_image(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("xai")
    if not key:
        raise ProviderError("xai: XAI_API_KEY not configured", code="no_key", retryable_next_route=True)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {"model": model, "prompt": req.prompt, "response_format": "b64_json"}
    if req.references:
        body["image_url"] = _data_uri(req.references[0])
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post("https://api.x.ai/v1/images/generations", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ProviderError(f"xai: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    if resp.status_code >= 400:
        raise _classify_http_error(resp, "xai")
    item = (resp.json().get("data") or [{}])[0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        raw = httpx.get(item["url"], timeout=60.0).content
    else:
        raise ProviderError("xai: empty image response", code="empty_response")
    out_path, digest = _save_bytes(req.out_dir, "generated.png", raw)
    return MediaResult(status="ok", route="api:xai", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)


def call_xai_video(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("xai")
    if not key:
        raise ProviderError("xai: XAI_API_KEY not configured", code="no_key", retryable_next_route=True)
    if not req.references:
        raise ProviderError("xai video requires at least one reference frame", code="invalid_request")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "model": model,
        "prompt": req.prompt,
        "image_url": _data_uri(req.references[0]),
        "duration": req.duration_seconds,
        "resolution": req.resolution,
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post("https://api.x.ai/v1/videos/generations", headers=headers, json=body)
            if resp.status_code >= 400:
                raise _classify_http_error(resp, "xai")
            job = resp.json()
            req_id = job.get("request_id") or job.get("id")
            if not req_id:
                raise ProviderError("xai video: missing request_id", code="empty_response")
            for _ in range(90):
                poll = client.get(f"https://api.x.ai/v1/videos/{req_id}", headers=headers)
                if poll.status_code >= 400:
                    raise _classify_http_error(poll, "xai")
                pdata = poll.json()
                video_url = (pdata.get("video") or {}).get("url") or pdata.get("url")
                if video_url:
                    raw = client.get(video_url, timeout=120.0).content
                    out_path, digest = _save_bytes(req.out_dir, "generated.mp4", raw)
                    return MediaResult(status="ok", route="api:xai", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd, job_id=str(req_id))
                if str(pdata.get("status", "")).lower() in ("failed", "error", "cancelled"):
                    raise ProviderError(f"xai video failed: {pdata}", code="job_failed")
                time.sleep(3.0)
    except httpx.HTTPError as exc:
        raise ProviderError(f"xai video: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    raise ProviderError("xai video: timed out waiting for completion", code="timeout")


def call_fal_media(req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    key = get_api_key("fal")
    if not key:
        raise ProviderError("fal: FAL_KEY not configured", code="no_key", retryable_next_route=True)
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {"prompt": req.prompt}
    if req.references:
        body["image_url"] = _data_uri(req.references[0])
    if req.kind == "video":
        body["duration"] = str(req.duration_seconds)
    url = f"https://fal.run/{model}"
    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ProviderError(f"fal: network error: {exc}", code="not_sent", retryable_next_route=True) from exc
    if resp.status_code >= 400:
        raise _classify_http_error(resp, "fal")
    data = resp.json()
    if req.kind == "image":
        media_url = ((data.get("images") or [{}])[0]).get("url") or (data.get("image") or {}).get("url")
        filename = "generated.png"
    else:
        media_url = (data.get("video") or {}).get("url")
        filename = "generated.mp4"
    if not media_url:
        raise ProviderError(f"fal: response missing media url for {model}", code="empty_response")
    raw = httpx.get(media_url, timeout=120.0).content
    out_path, digest = _save_bytes(req.out_dir, filename, raw)
    return MediaResult(status="ok", route="api:fal", model=model, artifact_path=out_path, sha256=digest, estimate_usd=est_usd)


def dispatch_api(provider: str, req: MediaRequest, model: str, est_usd: float) -> MediaResult:
    if provider == "gemini" and req.kind == "image":
        return call_gemini_image(req, model, est_usd)
    if provider == "openai" and req.kind == "image":
        return call_openai_image(req, model, est_usd)
    if provider == "openrouter" and req.kind == "image":
        return call_openrouter_image(req, model, est_usd)
    if provider == "xai" and req.kind == "image":
        return call_xai_image(req, model, est_usd)
    if provider == "xai" and req.kind == "video":
        return call_xai_video(req, model, est_usd)
    if provider == "fal":
        return call_fal_media(req, model, est_usd)
    raise ProviderError(f"Unsupported API provider/kind combination: {provider}/{req.kind}", code="unsupported")
