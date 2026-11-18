"""Runs the assembly of a big Comprovante in its own process and prints what it cost.

Usage: `python -m tests.support.comprovante_memory_runner <manifest.json> <output.pdf>`, with the
manifest `{"documents": [paths], "pages_per_document": n}`. The 400 pages are spread over 16
activities (two a group, eight groups), so the output has 1 + 2 + 8 + 400 = 411 pages. The
process is separate so that the peak is the one of the assembly and nothing else.

The peak is `VmHWM` of `/proc/self/status`, the high-water mark of the resident memory of this
process. `ru_maxrss` is not used: on Linux it also carries the peak of the parent from before the
`exec` (a test run that had grown to 600 MB reported 663 MB for an assembly of 82 MB).
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

from app.domain.entities.comprovante import ComprovanteLayout, LayoutActivity, LayoutPage
from app.domain.rules.comprovante_plan import plan_comprovante
from app.infrastructure.documents.comprovante_assembler import PdfComprovanteAssembler
from app.infrastructure.documents.front_matter import TOC_CAPACITY
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity
from tests.unit.infrastructure.comprovante_support import front

ACTIVITIES = 16
PAGES_PER_ACTIVITY = 25


def peak_mb() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) / 1024  # the value is in KB
    raise RuntimeError("VmHWM not found: the memory test needs Linux")


def main(manifest_path: str, output: str) -> None:
    manifest = json.loads(Path(manifest_path).read_text())
    per_document = manifest["pages_per_document"]
    ids = [uuid4() for _ in manifest["documents"]]
    files = dict(zip(ids, map(Path, manifest["documents"]), strict=True))
    activities, entries = [], []
    for k in range(ACTIVITIES):
        group = k // 2 + 1
        activity = make_activity(group, 1, title=f"Atividade {k + 1}")
        activities.append(activity)
        pages = []
        for g in range(k * PAGES_PER_ACTIVITY, (k + 1) * PAGES_PER_ACTIVITY):
            pages.append(LayoutPage(ids[g // per_document], g % per_document + 1))
        entries.append(LayoutActivity(activity.id, tuple(pages), group, 1))
    plan = plan_comprovante(ComprovanteLayout(PROCESS_ID, tuple(entries)), activities, TOC_CAPACITY)
    before = peak_mb()
    # 400 pages of 224 KB come to 88 MB, above the 60 MB limit of the product: the limit is
    # raised here because the subject of the test is the memory, not the size refusal.
    result = PdfComprovanteAssembler(max_output_bytes=200 * 1024 * 1024).assemble(
        plan, front({i: f"scan_{n}.pdf" for n, i in enumerate(ids)}), files.__getitem__,
        Path(output),
    )  # fmt: skip
    print(
        json.dumps(
            {
                "pages": result.pages,
                "size_bytes": result.size_bytes,
                "peak_mb": peak_mb(),
                "before_mb": before,
                "first_pages": [e.first_page for e in plan.toc if e.activity_id],
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
