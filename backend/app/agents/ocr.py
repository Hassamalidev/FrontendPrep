"""Optional handwriting OCR for uploaded answer sheets.

**What this honestly is.** Handwriting recognition is not a solved problem, and
this platform has no cloud OCR by design. Tesseract reads neat print reasonably
and cursive badly, so the output here is a *draft transcription* the candidate
corrects before anything is analysed -- never an authoritative reading. The API
and the UI are both built around that: OCR fills the boxes, the human confirms
them, and the analyser only ever sees confirmed text.

**What it never does.** It does not store the image. The bytes are decoded,
read, and dropped; only text survives the request. That keeps candidate
handwriting out of the database entirely, and keeps a 0.5 GB budget viable when
a WAT sheet photo is 3 MB.

Degrades the same way ``nlp.py`` does: no Pillow, no tesseract, or no binary on
the host all mean ``available()`` is False and the caller falls back to manual
transcription, which is still a useful feature on its own.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.config import settings

_IMPORT_NOTE: str | None = None


@lru_cache(maxsize=1)
def _backend() -> tuple[object | None, object | None]:
    """Return (Image module, pytesseract module) or (None, None)."""
    global _IMPORT_NOTE

    if not settings.OCR_ENABLED:
        _IMPORT_NOTE = "disabled by OCR_ENABLED"
        return None, None
    try:
        from PIL import Image, ImageFilter, ImageOps  # noqa: F401
    except ImportError:
        _IMPORT_NOTE = "Pillow is not installed"
        return None, None
    try:
        import pytesseract
    except ImportError:
        _IMPORT_NOTE = "pytesseract is not installed"
        return None, None

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        # The wrapper imports fine without the binary; only this call proves it.
        _IMPORT_NOTE = "the tesseract binary is not on PATH"
        return None, None

    _IMPORT_NOTE = None
    return Image, pytesseract


def available() -> bool:
    return _backend()[0] is not None


def note() -> str | None:
    _backend()
    return _IMPORT_NOTE


@dataclass(slots=True)
class Line:
    """One transcribed line, with the number the candidate wrote beside it."""

    index: int | None          # the "12." at the start of the line, if present
    text: str
    confidence: float = 0.0


@dataclass(slots=True)
class Transcription:
    lines: list[Line] = field(default_factory=list)
    engine: str = "none"
    note: str | None = None
    width: int = 0
    height: int = 0
    mean_confidence: float = 0.0

    @property
    def numbered(self) -> dict[int, str]:
        """Lines that carried their own number, keyed by it."""
        return {line.index: line.text for line in self.lines if line.index is not None}


# A candidate numbers their sheet "1." / "1)" / "12 -". Capture that so a line
# can be matched to the item it answers even when a few lines are unreadable.
_NUMBERED = re.compile(r"^\s*(\d{1,3})\s*[.)\-:]\s*(.+)$")
_NOISE = re.compile(r"[^\w\s.,;:!?'\"()&%/-]")


def _clean(raw: str) -> str:
    """Strip the speckle OCR invents from paper grain, keep real punctuation."""
    text = _NOISE.sub(" ", raw)
    return " ".join(text.split())


def _preprocess(image, Image):
    """Grayscale, upscale small photos, autocontrast, sharpen.

    Phone photos of ruled paper are the hard case: low contrast ink, shadows and
    a slight angle. This is the cheap 80% -- it lifts tesseract's hit rate
    noticeably without pulling in OpenCV, which would not fit the memory budget.
    """
    from PIL import ImageFilter, ImageOps

    image = ImageOps.exif_transpose(image)      # honour the phone's rotation flag
    image = image.convert("L")

    # Tesseract wants roughly 300 DPI; a small upload is worth upscaling.
    if image.width < 1200:
        scale = 1200 / image.width
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)), Image.LANCZOS
        )

    image = ImageOps.autocontrast(image, cutoff=2)
    return image.filter(ImageFilter.SHARPEN)


def transcribe(data: bytes) -> Transcription:
    """Best-effort read of an answer sheet. Never raises."""
    Image, pytesseract = _backend()
    result = Transcription(engine="tesseract" if Image else "none", note=note())

    if Image is None:
        return result

    try:
        with Image.open(io.BytesIO(data)) as raw:
            image = _preprocess(raw, Image)
            result.width, result.height = image.size

            # PSM 6 -- "a single uniform block of text" -- suits a numbered sheet
            # better than the default, which hunts for columns and finds ruling.
            frame = pytesseract.image_to_data(
                image,
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )
    except Exception as exc:
        result.note = f"could not read the image: {type(exc).__name__}"
        return result

    # image_to_data returns one row per word; regroup into lines.
    grouped: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    for i, word in enumerate(frame.get("text", [])):
        if not word or not word.strip():
            continue
        key = (frame["block_num"][i], frame["par_num"][i], frame["line_num"][i])
        try:
            confidence = float(frame["conf"][i])
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0:
            continue
        grouped.setdefault(key, []).append((word, confidence))

    confidences: list[float] = []
    for key in sorted(grouped):
        words = grouped[key]
        text = _clean(" ".join(w for w, _ in words))
        if not text:
            continue
        line_confidence = sum(c for _, c in words) / len(words)
        confidences.append(line_confidence)

        match = _NUMBERED.match(text)
        if match:
            result.lines.append(
                Line(index=int(match.group(1)), text=match.group(2).strip(), confidence=line_confidence)
            )
        else:
            result.lines.append(Line(index=None, text=text, confidence=line_confidence))

    result.mean_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
    return result


def align(transcription: Transcription, item_count: int) -> list[str]:
    """Map transcribed lines onto ``item_count`` answer slots.

    Prefers the numbers the candidate wrote; falls back to reading order for the
    rest. Any slot with no line stays empty rather than being guessed at -- a
    wrong guess silently attributes words to the wrong stimulus, which would
    corrupt the analysis in a way the candidate could not see.
    """
    slots = [""] * item_count
    numbered = transcription.numbered

    for index, text in numbered.items():
        if 1 <= index <= item_count:
            slots[index - 1] = text

    leftovers = [line.text for line in transcription.lines if line.index is None]
    cursor = 0
    for position in range(item_count):
        if slots[position] or cursor >= len(leftovers):
            continue
        # Only fill by position when the candidate numbered nothing at all;
        # mixing the two orders is how lines end up under the wrong word.
        if not numbered:
            slots[position] = leftovers[cursor]
            cursor += 1

    return slots
