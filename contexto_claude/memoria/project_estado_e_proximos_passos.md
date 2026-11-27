---
name: project-estado-e-proximos-passos
description: "State of PSI3442 work at 2026-11-27 (Linux Mint): Android bridge app built and verified end to end in the emulator; what blocks flying Task 1 on the real drone"
metadata:
  node_type: memory
  type: project
  originSessionId: 3724ddc4-cd94-4220-813d-07b961a51983
  modified: 2026-11-27T15:31:39.576Z
---

On 2026-11-27, on the Linux Mint notebook (this machine), Claude built `android_ponte/` (Kotlin bridge app, DJI MSDK 5.20.1 behind a `Drone` interface; variants `emulador` = fake drone, `celular` = real SDK). The celular variant compiles and packages against the real SDK. Task 1 ran end to end in an AOSP emulator through the app with the real ROS 2 system (concluded, 10 Hz telemetry, max vertical error 0.069 m). The 8 implementation adjustments are now in the SysML model.

Verified fact: the MSDK talks to the RC in USB accessory mode, so an emulator on a laptop cannot reach the RC. Real flight = app on a phone cabled to the RC, notebook connected over Wi-Fi (`host_ponte:=<IP>`). The SysML model and diagrams still say "Android emulado": update them only after the user confirms.

**Why:** the user asked (2026-11-27) to work on the emulation module and close Task 1 on the physical drone.

**How to apply:** next steps and what depends on the user are in the "Pendências" section of CLAUDE.md: RC-N2/N3 (H7), an ARM64 Android phone, DJI App Key for package br.usp.psi3442.ponte, the 15 % critical battery value, and approval for the model update. Before T01, run T00 (`ensaios/teste_eixos.py`): the roll/pitch-to-north/east mapping (`DroneDji.ROLL_E_NORTE`) is not documented by DJI. Use an AOSP (not google_apis) emulator image. Related: [[project-arquitetura-ros2]], [[feedback-push-github]].
