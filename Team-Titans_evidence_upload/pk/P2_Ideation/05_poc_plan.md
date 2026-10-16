# Bounded PoC test plan (I02, provisional)
Claim: on 30 team-photographed labels, I02 matches a manual reference on >=90% of field checks and flags low-confidence fields, in <=50% of manual time.
Design: 30 photos (10 hard: curved, shiny, regional language, sticker) x 7 fields = 210 checks. Reference by two members, Mentor-checked. Comparator: timed manual checklist (I01), order alternated. Small design, not statistically powered.
Pass thresholds: >=189/210 correct; 0 of 30 labels with a wrong "present" result without an UNCERTAIN flag; <=50% of manual time, <=10 s processing, rollback <=5 min, cost <=Rs 1,000 (estimated).
Boundary: team-photographed retail packs, no personal data, isolated environment, no enforcement use. Mentor approval of protocol pending.
Stop/pivot: if accuracy or guardrail fails, fall back to I01, tune OCR, or test I03. Do not re-label targets as results.
