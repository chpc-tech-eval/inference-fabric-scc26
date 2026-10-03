# Technical Poster Proposal / Storyboard

## Working title

**Benchmarking Open LLM Inference Runtimes Across CPU, A100 and H200 Resources**

The poster is not the paper pasted onto a large page. It should let a technically literate viewer understand the problem, architecture, method and most important evidence in roughly **2–3 minutes**, then provide enough detail for a deeper discussion.

## Recommended format

Unless the final event specifies another size, design for **A0 portrait (841 × 1189 mm)** or an equivalent large-format three-column layout. Keep the source editable so it can be resized later.

### Visual hierarchy

- Title readable from several metres away.
- One-sentence research question directly below the title.
- 3-column flow with strong section headers.
- Approximately 40–55% of the poster area should be diagrams, plots, tables or structured visual evidence rather than paragraphs.
- Use short bullets; avoid blocks of prose.
- Keep colours/highlighting restrained and accessible; do not encode meaning by colour alone.
- Include project/repository QR code only if the destination is safe/public and stable.

## Storyboard

```text
┌─────────────────────────────────────────────────────────────────────┐
│ TITLE / AUTHORS / AFFILIATION / ONE-SENTENCE RESEARCH QUESTION      │
├──────────────────────┬──────────────────────┬───────────────────────┤
│ 1. PROBLEM & WHY     │ 3. METHOD           │ 5. KEY RESULTS        │
│    IT MATTERS        │                      │                       │
│                      │ experiment/scenario  │ 1--3 strong figures  │
│ 2. ARCHITECTURE      │ versions/resources  │ + compact result table│
│    (large figure)    │ reproducibility      │                       │
├──────────────────────┼──────────────────────┼───────────────────────┤
│ 4. EVIDENCE /        │ 6. INTERPRETATION   │ 7. LIMITATIONS,       │
│    METRICS SOURCES   │    & LESSONS         │    CONCLUSION,        │
│                      │                      │    FUTURE WORK        │
├──────────────────────┴──────────────────────┴───────────────────────┤
│ REPRODUCIBILITY STRIP: Git SHA · image digest · test ID · QR/link  │
└─────────────────────────────────────────────────────────────────────┘
```

## Project-specific figures to plan now

- inference-fabric architecture
- benchmark matrix across runtime/hardware
- TTFT or latency distribution
- throughput versus concurrency and resource utilisation

Do not fabricate these figures before the experiments. Instead, create the scripts/data-capture path during Weeks 3–5 so the final visual is generated from real evidence.

## Suggested content by panel

### 1. Problem / motivation
- 2–4 bullets maximum.
- State the engineering/scientific question, not the whole programme history.

### 2. Architecture
- One large diagram showing trust/resource boundaries.
- Clearly distinguish workstation, Sebowa, Kubernetes and A100/H200 when relevant.

### 3. Method
- 4–6 numbered steps.
- Include what was held constant, what varied and how success was measured.

### 4. Evidence sources
- Prometheus metrics, Wazuh/Suricata logs, ACP task records, benchmark output, CI artifacts, etc. as relevant.
- Show how provenance ties the result back to code/configuration.

### 5. Key results
- Choose the **two or three strongest results**, not every measurement.
- Every axis/unit/legend must be readable at print size.

### 6. Interpretation / lessons
- What did the evidence actually teach you?
- Separate observation from explanation.

### 7. Limitations / conclusion / future work
- Be explicit about POC scale, virtualisation, limited test duration/sample size or shared hardware constraints.
- Finish with one evidence-supported conclusion and 2–3 next steps.

## Reproducibility strip

Include a small footer/strip with the accepted Git SHA, image digest(s), experiment/run identifier(s), and repository link/QR if public. Never print credentials, internal secrets or unnecessarily sensitive network details.

## Poster review checklist

- [ ] Can the research question be understood in 10 seconds?
- [ ] Is the architecture figure readable without narration?
- [ ] Are the most important measured results visually dominant?
- [ ] Are all numbers/figures traceable to retained evidence?
- [ ] Are units, legends and labels readable at final print size?
- [ ] Does the poster state limitations rather than overselling the POC?
- [ ] Is the conclusion supported by the displayed evidence?
- [ ] Can every team member present the whole poster?
