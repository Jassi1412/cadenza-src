# Files shared through Git

The Git distribution contains application/specification sources, the compiler required to reproduce them, scores, evaluation scripts, raw JSON/CSV/MIDI/traces, frozen expectations, Markdown/LaTeX reports and original scientific evidence.

Local ZIP backups, installed dependencies, Python bytecode, duplicate `.log` output and rendered paper previews are omitted. They remain on the original machine; no local evidence is deleted. Previews can be rebuilt with `scripts/build-paper.sh`. Full subprocess output, warnings and verdicts remain in the committed JSON evidence.

The original archive's frozen `MANIFEST.json` is unchanged. [SHARING-EXCLUSIONS.json](archive/v1-original/SHARING-EXCLUSIONS.json) identifies 19 expendable entries omitted from Git and preserves their original SHA-256 hashes and reasons. A complete local archive verifies all 421 original entries; the Git distribution verifies the 402 retained entries. An excluded file is still hash-checked whenever present. Missing files outside that declaration remain errors.

Scientific application/specification hashes remain enforced. ZIP backups, bytecode and Git ignore/attribute configuration are outside the scientific source audit; the original recorded hashes remain preserved in the provenance. Git attributes preserve evaluation and score bytes without line-ending conversion so their hashes survive checkouts.

No timing, verdict, expectation or scientific report is changed by this packaging step. Regenerating metadata or experiments should follow the archive-before-rerun instructions. The original reports describe the complete archive at experiment time; sharing exclusions describe the smaller Git distribution.
