# Short IEEE-style technical paper

The Week-6 paper is a **3–5 page, two-column technical paper** intended to teach concise conference/journal-style scientific engineering communication. The included `main.tex` uses the standard `IEEEtran` conference class as a practical two-column scaffold.

> This is a programme template, not a guarantee that it matches the final author kit of a future IEEE venue. If the work is later submitted externally, use that venue's current official instructions/template.

## Working title

**Benchmarking Open LLM Inference Runtimes Across CPU, A100 and H200 Resources**

Change the title as your actual contribution becomes clear. Do not force the final paper to match the scaffold.

## Page budget

A useful 4-page target is:

| Section | Approximate space |
| --- | ---: |
| Abstract + keywords | 0.2 page |
| I. Introduction | 0.5 page |
| II. System/Background | 0.6 page |
| III. Methodology | 0.8 page |
| IV. Results | 1.0–1.3 pages |
| V. Discussion/Limitations | 0.5 page |
| VI. Conclusion | 0.2–0.3 page |
| References | remaining space / venue policy |

The paper should focus on **runtime portability, latency, throughput, concurrency, memory pressure and workload-aware placement**.

## Evidence rules

- Do not invent or back-fill measurements.
- Every number should be recoverable from retained logs/results or an experiment record.
- Record Git commit(s), container image digest(s), relevant hardware/resource allocation and test conditions.
- Distinguish measured result from interpretation.
- Include failures/limitations when they materially affect the conclusion.
- Use screenshots sparingly; prefer architecture diagrams, plots and compact tables.

## Suggested paper figures/tables

- inference-fabric architecture
- benchmark matrix across runtime/hardware
- TTFT or latency distribution
- throughput versus concurrency and resource utilisation

## Files

- `main.tex` — two-column paper scaffold;
- `references.bib` — starter bibliography file;
- `figures/README.md` — figure provenance rules.

Compile using an IEEEtran-capable LaTeX environment/Overleaf. If you do not normally use LaTeX, the section structure is still a useful writing outline; ask the mentor before changing the submission format.
