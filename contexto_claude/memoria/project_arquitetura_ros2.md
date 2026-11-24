---
name: project-arquitetura-ros2
description: Architecture decision (2026-11-23) for PSI3442 P2 — Linux notebook with ROS 2 runs the missions; emulated Android with DJI MSDK app is only the comms bridge; drone is one black-box component; decomposition targets the missions
metadata:
  node_type: memory
  type: project
  originSessionId: 3724ddc4-cd94-4220-813d-07b961a51983
  modified: 2026-11-24T04:01:40.699Z
---

Since 2026-11-23 the architecture is: Linux notebook running ROS 2 hosts all mission logic (mission manager, Missão 1 voo de familiarização, Missão 2 balões, estimation, control, perception, supervision, logging). An emulated Android on the same notebook runs a DJI Mobile SDK v5 bridge app; it talks to ROS 2 over TCP and to the RC over USB passthrough. Drone (DJI Mini 4 Pro) + RC are black-box components.

**Why:** user reframed the project as a software problem: "o modelo de drone é dado... o alvo da decomposição passa a ser as missões do drone em si". This replaced the earlier phone-based (Celular Android + Kotlin mission logic) architecture.

Verified 2026-11-24 in DJI MSDK v5 release notes: Mini 4 Pro supported from MSDK 5.13.0 (current 5.20.1) only with DJI RC N2 or RC N3; DJI RC 2 not listed; no phone-direct Wi-Fi control for this model. User said (2026-11-24) the team has no RC, only computer + phone — must get an RC-N2/N3 from the course kit (hypothesis H7 in the intermediate report). The team's own Android phone is the fallback host for the bridge app.

**How to apply:** functional decomposition (levels 0/1/n) focuses on missions and ROS 2 nodes, not drone hardware. Known feasibility risks to keep testing early: MSDK v5 ships ARM native libs (emulator needs ARM translation), RC USB passthrough into the emulator, MSDK online app-key activation. Diagrams: diagramas/gerar_diagramas.py. Related: [[feedback-adapt-existing]], [[user-profile]].
