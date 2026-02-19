# app/student_knowledge/fetcher.py
"""
Content fetchers for student uploads.
Handles files (PDF/TXT/MD/DOCX), YouTube transcripts, and web pages.
"""

import os
import time
import hashlib
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from app.core.logging import log_info, log_error, log_warning


def compute_fingerprint(content: str) -> str:
    """Compute SHA-256 fingerprint for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Execute a function with exponential backoff on transient failures."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log_warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                log_error(f"All {max_retries} attempts failed: {e}")
    if last_error:
        raise last_error
    raise Exception("Retry loop finished without success")


def fetch_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract text from uploaded file bytes.
    Returns: {text, title, structure, content_type}
    """
    text = ""
    title = os.path.splitext(filename)[0]
    content_type = "document"
    structure = {"headings": [], "sections": []}

    suffix = os.path.splitext(filename)[1].lower()

    # Write to temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            text, structure = _extract_pdf(tmp_path)
            content_type = "pdf"
        elif suffix in [".txt", ".md"]:
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            content_type = "text"
            structure = _detect_structure(text)
        elif suffix in [".docx"]:
            text = _extract_docx(tmp_path)
            content_type = "docx"
            structure = _detect_structure(text)
        elif suffix in [".html", ".htm"]:
            import trafilatura
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()
            text = trafilatura.extract(html_content) or ""
            content_type = "html"
            structure = _detect_structure(text)
        else:
            # Fallback: try plain text read
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            content_type = "text"
            structure = _detect_structure(text)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not text.strip():
        raise ValueError(f"Could not extract text from file: {filename}")

    log_info(f"Extracted {len(text)} chars from {filename} ({content_type})")

    return {
        "text": text,
        "title": title,
        "structure": structure,
        "content_type": content_type,
        "fingerprint": compute_fingerprint(text),
    }


def fetch_youtube(url: str) -> Dict[str, Any]:
    """
    Fetch YouTube video transcript with timestamps.
    Returns: {text, title, timestamps, structure}
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extract video ID
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")

    def _fetch():
        try:
            return YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            # Fallback to list_transcripts to find any available transcript
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Try generated English, then any generated
                try:
                    return transcript_list.find_generated_transcript(['en']).fetch()
                except:
                    for transcript in transcript_list:
                         return transcript.fetch()
            except Exception as e:
                raise ValueError(f"No transcript available for video {video_id}: {e}")

    try:
        transcript_items = _retry_with_backoff(_fetch)
    except Exception as e:
        log_warning(f"YouTube transcript fetch failed for {video_id}: {e}")
        # Return object that agent.py will recognize as a failure but we raise error here
        # to be caught by clean handling in agent.py
        raise ValueError(f"Could not retrieve transcript: {e}")

    # Build text with timestamp context
    text_parts = []
    timestamps = []
    for item in transcript_items:
        text = item["text"]
        if not text: continue
        text_parts.append(text)
        timestamps.append({
            "text": text,
            "start": item["start"],
            "duration": item.get("duration", 0),
        })

    full_text = " ".join(text_parts)
    if not full_text.strip():
        raise ValueError("Transcript was empty")

    title = f"YouTube: {video_id}"

    # Try to get video title
    try:
        title = _get_youtube_title(video_id) or title
    except Exception:
        pass

    log_info(f"Fetched YouTube transcript: {len(transcript_items)} segments, {len(full_text)} chars")

    return {
        "text": full_text,
        "title": title,
        "timestamps": timestamps,
        "structure": {"type": "video", "segments": len(transcript_items)},
        "content_type": "youtube",
        "fingerprint": compute_fingerprint(full_text),
        "transcript_status": "generated" if "generated" in str(transcript_items) else "manual" 
    }


def fetch_website(url: str) -> Dict[str, Any]:
    """
    Fetch and extract readable content from a web page.
    Returns: {text, title, structure}
    """
    import trafilatura

    def _fetch():
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"Failed to download webpage: {url}")
        return downloaded

    html = _retry_with_backoff(_fetch)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)

    if not text or not text.strip():
        raise ValueError(f"Failed to extract content from: {url}")

    # Try to extract title
    title = url
    try:
        from trafilatura.metadata import extract_metadata
        meta = extract_metadata(html)
        if meta and meta.title:
            title = meta.title
    except Exception:
        pass

    structure = _detect_structure(text)

    log_info(f"Fetched website: {len(text)} chars from {url}")

    return {
        "text": text,
        "title": title,
        "structure": structure,
        "content_type": "website",
        "fingerprint": compute_fingerprint(text),
    }


# ─── Internal helpers ───

def _extract_pdf(path: str):
    """Extract text and structure from PDF."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    text_parts = []
    headings = []

    for i, page in enumerate(reader.pages):
        extracted = page.extract_text()
        if extracted:
            text_parts.append(extracted)
            # Simple heading detection from first line of each page
            lines = extracted.strip().split("\n")
            if lines and len(lines[0]) < 100:
                headings.append({"text": lines[0].strip(), "page": i + 1})

    full_text = "\n".join(text_parts)
    structure = {"headings": headings, "page_count": len(reader.pages)}
    return full_text, structure


def _extract_docx(path: str) -> str:
    """Extract text from DOCX file."""
    try:
        import docx
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        log_warning("python-docx not installed. Falling back to plain text read.")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def _detect_structure(text: str) -> Dict[str, Any]:
    """Detect headings and sections from plain text."""
    lines = text.split("\n")
    headings = []
    sections = []
    current_section = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Detect markdown-style headings or ALL-CAPS headings
        is_heading = (
            stripped.startswith("#") or
            (stripped.isupper() and len(stripped) < 80 and len(stripped) > 3) or
            (stripped.endswith(":") and len(stripped) < 60)
        )
        if is_heading:
            heading_text = stripped.lstrip("#").strip().rstrip(":")
            headings.append({"text": heading_text, "line": i})
            if current_section:
                sections.append(current_section)
            current_section = {"heading": heading_text, "start_line": i}

    if current_section:
        sections.append(current_section)

    return {"headings": headings, "sections": sections}


def _extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0].split("#")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0].split("#")[0]
    elif "/embed/" in url:
        return url.split("/embed/")[-1].split("?")[0].split("#")[0]
    return None


def _get_youtube_title(video_id: str) -> Optional[str]:
    """Try to get YouTube video title via oembed API."""
    try:
        import urllib.request
        import json
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(oembed_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title")
    except Exception:
        return None
