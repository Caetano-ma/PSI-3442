---
name: project-estado-e-proximos-passos
description: "State of PSI3442 work at 2026-11-24 (C2 + Gazebo done on Windows) and the handoff plan — user will move Claude to a Linux Mint machine and wants Claude to do \"todo o restante\""
metadata:
  node_type: memory
  type: project
  originSessionId: 62df1d49-aea6-42ee-931f-ae3b4e2778f5
  modified: 2026-11-24T18:07:20.150Z
---

On 2026-11-24 (Windows 11 machine, Docker Desktop) Claude finished cycle C2 (ROS 2 workspace, Tarefa 1 nodes, kinematic simulator, tests T05/T07/T08/T10) and the Tarefa 1 simulation in Gazebo Harmonic (package psi3442_gazebo). Both verified end to end and pushed.

The user then said they will soon put Claude on a **Linux Mint** machine and want Claude to do **all the remaining work** there. Nothing Android/Kotlin exists yet: no app, no Android SDK/emulator/adb installed, C1 feasibility not tested.

**Why:** the user wants continuity across machines; this conversation's history is not in the (public) repo, so this memory + CLAUDE.md are the bridge.

**How to apply:** on the Linux Mint machine, start from the "Plano para a máquina Linux Mint" section of CLAUDE.md: install ROS 2 Jazzy + ros-jazzy-ros-gz natively, re-run tests and the Gazebo sim, update the SysML model with the adjustments in ros2_ws/README.md, then C1 (Android emulator + MSDK v5 feasibility) and C3 (Kotlin bridge app with the DJI SDK behind an interface and a fake implementation, tested against the ROS 2 side). Still waiting on the user: RC-N2/N3 from the kit (H7), DJI developer account + App Key, confirmation of bateria_critica_pct = 15 %. Related: [[project-arquitetura-ros2]], [[feedback-push-github]], [[feedback-instrucoes-terminais]].
