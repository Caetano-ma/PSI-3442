---
name: feedback-instrucoes-terminais
description: "When telling the user how to run multi-terminal setups (simulation, operator, panel), say exactly which terminal runs what and what each screen looks like"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 62df1d49-aea6-42ee-931f-ae3b4e2778f5
  modified: 2026-11-24T18:07:24.383Z
---

Give run instructions terminal by terminal: which command goes in which terminal, what the user should see, and which screens accept typing.

**Why:** on 2026-11-24 the user ran the Gazebo sim and waited with the drone parked at A because no command had been sent. Later they opened the panel (`operador.sh painel`) thinking it was the operator, and the terminal looked "stuck". They also mixed up which terminal corresponds to the real system.

**How to apply:**
- State that the simulation does nothing until "executar tarefa 1" is sent, unless `comando_automatico:=true` is passed.
- Distinguish the operador (accepts typing) from the painel (display only).
- When the user reports "nothing happens", inspect the container (`/tarefa/status`, running processes, node logs) before answering.
Related: [[project-estado-e-proximos-passos]].
