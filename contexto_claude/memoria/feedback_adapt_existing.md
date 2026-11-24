---
name: feedback-adapt-existing
description: "When the user supplies their own diagram/model, adapt it minimally (keep layout, blocks, colors) instead of redesigning from scratch"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3724ddc4-cd94-4220-813d-07b961a51983
  modified: 2026-11-16T11:22:36.088Z
---

Adapt the user's existing diagrams/models by adding what is missing; do not redraw from zero in a new structure.

**Why:** I replaced their level 0/1 drone diagrams with brand-new Graphviz diagrams (functional lanes F1–F20); user said "ficou ruim" and asked to keep their division, which they consider generic enough to reuse.

**How to apply:** keep their block names, layout and color scheme; mark additions clearly; only remove items that are factually wrong, and say so. Related: [[user-profile]].
