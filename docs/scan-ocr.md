# LabelGuard AI — Scan Intake, Image Quality & OCR (Phase 12)

**Status:** `[IMPLEMENTED]` — scan intake, image validation, quality checks, OpenCV
preprocessing, a PaddleOCR adapter, and normalization to the Phase 11 OCR contract,
with tests.
**Not in this phase:** declaration extraction, Legal Metrology assessment, rule-engine
changes, verification, nutrition, ingredient intelligence, evidence, PDF, the public
`/scan` API, barcode/QR, YOLO, mobile wiring. Those remain `[PLANNED]`.

This document describes the first pipeline segment:

```text
PRODUCT IMAGE → SCAN INTAKE → IMAGE QUALITY → IMAGE PROCESSING → OCR → OCR CONTRACT
```

The guiding invariant: **Phase 12 produces an image, an image-quality report, and OCR
output — nothing more.** It never decides compliance, never extracts declarations, and
never turns recognised text into values. `NO_TEXT_DETECTED` is not "a declaration is
missing"; an OCR failure is not "non-compliant".

---

## 1. Architectural position

```text
 bytes ──▶ intake ──▶ PreparedImage ──┬─▶ quality  ──▶ ImageQualityReport ─┐
 (upload)  (decode,   (BGR array,     │   (blur /                          │
           EXIF)       scan_id)       │    brightness /                    ├─▶ ScanProcessingResult
                                      │    resolution)                     │
                                      └─▶ preprocess ─▶ OCR provider ──▶ OCRResponse (regions = OCRResult)
                                          (resize/CLAHE)  (PaddleOCR)   ▲
                                                                        │
                                            RawTextRegion ── normalize ─┘  (Phase 11 contract)
```

New packages, mirroring the existing `app/compliance/` domain-package layout:

- `app/imaging/` — `validation.py`, `intake.py`, `quality.py`, `preprocessing.py`,
  `pipeline.py`
- `app/ocr/` — `provider.py`, `paddle_adapter.py`, `normalization.py`, `service.py`
- `app/schemas/imaging.py` — container schemas that **reuse** the Phase 11
  `OCRResult` and adapt **down** to the Phase 11 `ImageQualityResult`.

## 2. The internal service (not a public API)

The single entry point is a function, per the phase scope — it is deliberately not
wired to a FastAPI route yet:

```python
from app.imaging import process_scan

result = process_scan(image_bytes, filename=None, content_type=None, provider=None)
# result: app.schemas.imaging.ScanProcessingResult
```

- `provider` is any object implementing `app.ocr.provider.OCRProvider`. If omitted, the
  pipeline uses PaddleOCR **only if it is installed**; otherwise OCR is reported as
  `PROCESSING_ERROR` (never a crash, never a legal statement).
- Hard intake faults raise `AppError`; everything else returns a `ScanProcessingResult`.

## 3. Scan intake (`app/imaging/intake.py`)

`load_scan(bytes, ...) -> PreparedImage` decodes the image **exactly once** and returns
a decoded, EXIF-upright BGR array plus a `scan_id` (`uuid4().hex`).

- **The original is never destroyed or overwritten.** Input `bytes` are immutable and
  never written to disk; decoding produces a new array; every later stage works on
  copies.
- **Orientation is EXIF-only.** A rotation recorded in EXIF tag 274 is applied and
  reported as `CORRECTED`; no metadata means `OK`; an unreadable tag means `UNKNOWN`
  (a warning, never a guess).
- `filename` / `content_type` are accepted for logging only and never used to decide
  the format.

## 4. Image validation (`app/imaging/validation.py`)

Cheap, dependency-free byte checks that run before any decode:

| Check | Failure | `AppError.code` | HTTP |
|-------|---------|-----------------|------|
| Non-empty | empty upload | `EMPTY_IMAGE` | 422 |
| Size ≤ `scan_max_file_bytes` | too large | `IMAGE_TOO_LARGE` | 413 |
| Format in `scan_supported_formats` | unsupported | `UNSUPPORTED_FORMAT` | 415 |
| Decodable | corrupt/truncated | `CORRUPTED_IMAGE` | 422 |
| Sane dimensions | 0-size / too large | `INVALID_DIMENSIONS` | 422 |

**Format is detected from magic bytes, never the extension:** JPEG (`FF D8 FF`),
PNG (`89 50 4E 47 0D 0A 1A 0A`), WEBP (`RIFF….WEBP`). A `.jpg` filename on a PDF is
still rejected.

## 5. Image quality (`app/imaging/quality.py`)

Three independent, standard metrics on the decoded image — kept **separate** (there is
no single global "legal confidence" score):

- **Blur** — variance of the Laplacian. Low variance ⇒ smeared edges ⇒ blurry
  (`is_blurry` when `score < image_blur_threshold`).
- **Brightness** — mean grayscale on 0–255; `TOO_DARK` / `TOO_BRIGHT` outside
  `[image_brightness_min, image_brightness_max]`.
- **Resolution** — width/height vs `image_min_width` / `image_min_height`.

`classify_quality(...)` folds these into an overall `ImageQualityStatus`:

- `UNUSABLE` — severe blur (score below half the threshold), **or** two or more
  independent problems compound.
- `WARNING` — any single problem, or a non-blocking caveat (unknown orientation).
- `OK` — otherwise.

This heuristic only gauges **OCR reliability**; it is never a compliance verdict.
`ImageQualityReport.to_image_quality_result()` adapts down to the Phase 11
`ImageQualityResult` (`UNUSABLE → usable=False`; `OK`/`WARNING → usable=True`).

## 6. Preprocessing (`app/imaging/preprocessing.py`)

`ImagePreprocessor.prepare_for_ocr(image)` chains modular steps, each returning a
**new** array so the original is preserved:

`resize (cap long edge at image_preprocess_max_dim) → grayscale → CLAHE contrast →
median denoise → (optional adaptive binarize) → back to 3-channel BGR`

Binarization is **opt-in** — detectors usually do better on the contrast-enhanced
natural image than on a hard threshold.

## 7. OCR provider & the PaddleOCR adapter

`OCRProvider` (a `Protocol`) has one method, `recognize(image) -> list[RawTextRegion]`.
`RawTextRegion` is the provider-neutral hand-off (raw text, raw score, polygon points).

`PaddleOCRProvider` (`app/ocr/paddle_adapter.py`):

- **imports `paddleocr` lazily**, inside `_ensure_engine` — importing the package does
  not import the heavy dependency, so the app and tests run without it;
- **builds the engine once per process** per language set (cached at module scope);
- exposes `available()` (a spec-probe that does not import the heavy module).

Architecture (spec §6): `PaddleOCR → PaddleOCRProvider → RawTextRegion → OCRResult`.
OCR adapts to the contract; the contract is unchanged.

## 8. Normalization to the Phase 11 contract (`app/ocr/normalization.py`)

A purely mechanical transform — **no interpretation of text**:

- `to_bbox(points)` → ordered, non-negative, image-clamped integer `[x1, y1, x2, y2]`
  that always satisfies the `OCRResult` invariant `x2 ≥ x1, y2 ≥ y1`.
- `normalize_region(raw)` → a Phase 11 `OCRResult` (confidence clamped to `[0, 1]`,
  text stripped).
- `build_ocr_response(...)` classifies the read:
  - no non-blank regions → `NO_TEXT_DETECTED` (mean confidence `None`);
  - mean confidence ≤ `ocr_low_confidence_threshold` → `LOW_CONFIDENCE`;
  - otherwise → `SUCCESS`.

`"MRP ₹50"` stays the string `"MRP ₹50"`. It never becomes `MRP = 50`.

## 9. OCR service (`app/ocr/service.py`)

`OCRService(provider).run(image, width, height, scale_x, scale_y)` runs the provider,
maps bboxes from the (possibly resized) OCR image back to the **original** coordinate
space, and delegates classification to `build_ocr_response`. Any provider exception
becomes `PROCESSING_ERROR` with a client-safe warning; the raw exception is logged, not
surfaced.

## 10. OCR states (`app/core/enums.py::OCRStatus`)

| State | Meaning | Not the same as |
|-------|---------|-----------------|
| `SUCCESS` | text read with acceptable mean confidence | "compliant" |
| `LOW_CONFIDENCE` | text read, mean confidence ≤ threshold | "non-compliant" |
| `NO_TEXT_DETECTED` | no text found on a valid image | "a declaration is missing" |
| `PROCESSING_ERROR` | OCR could not run (e.g. no engine) | any legal outcome |
| `INVALID_IMAGE` | the array handed to OCR was degenerate | corrupt-upload rejection |

## 11. Configuration (`app/core/config.py`)

All thresholds are environment-tunable `Settings` fields (none are legal thresholds):
`scan_max_file_bytes`, `scan_supported_formats`, `image_min/max_width/height`,
`image_blur_threshold`, `image_brightness_min/max`, `image_preprocess_max_dim`,
`ocr_languages`, `ocr_low_confidence_threshold`.

## 12. Enabling real OCR (optional, local only)

PaddleOCR is not installed by default. To try real recognition locally:

```bash
pip install paddlepaddle paddleocr
```

The first run downloads model weights over the network. No system-level components
(Docker, Hyper-V, Windows services) are required or modified. With the package present,
`process_scan(image_bytes)` uses it automatically; unit tests keep using a mock provider
and remain independent of the install.

## 13. Testing

`tests/imaging/` and `tests/ocr/` (67 tests). Images are generated deterministically
in-memory (numpy + OpenCV, Pillow for EXIF); OCR is mocked via `StubOCRProvider`, so the
suite never needs PaddleOCR or the network. Modules guard on
`pytest.importorskip("cv2")` so they skip cleanly where OpenCV is absent. A source-level
test asserts the imaging/OCR packages do not import the legal engine or the database.
