---
name: feedback-push-github
description: "After every change in the PSI 3442 project, commit and push to github.com/Caetano-ma/PSI-3442 (public); how to commit without touching git config"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3724ddc4-cd94-4220-813d-07b961a51983
  modified: 2026-11-23T12:36:59.848Z
---

Every change to the project must be committed and pushed to https://github.com/Caetano-ma/PSI-3442.git (branch main, public repo).

**Why:** user asked on 2026-11-23: "a partir de agora, sempre que houver alguma mudança suba no repositório".

**How to apply:** at the end of each change set, commit and push without waiting to be asked. git has no user.name/email configured and I must not change git config, so commit with
`git -c user.name=Caetano-ma -c user.email=281951699+Caetano-ma@users.noreply.github.com commit ...` (noreply keeps the personal e-mail out of a public repo) and push with
`git -c credential.helper= -c credential.helper='!gh auth git-credential' push`.
`*.docx` is git-ignored: the course statement (professor's document with his e-mail) is held back until the user confirms publishing it. Related: [[user-profile]].
