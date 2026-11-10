# ProofLoop AI — Milestone Roadmap (GSD)

Milestone v1: "Verifiable evidence intelligence".

| Phase | Name | Goal | Gate |
|---|---|---|---|
| 0 | Audit | Ground truth of empty repository | Audit doc + risk register |
| 1 | Spec freeze | Scope, architecture, API, design | Docs accepted, ADRs recorded |
| 2 | Landing | Public product story + entry | Responsive, CTAs work, no console errors |
| 3 | Shell + dashboard | Navigable app with real metrics | Routes work, data real |
| 4 | Input + claims | Ingestion and atomic claims | Deterministic tests + E2E submit |
| 5 | Research | Real sources and excerpts | Live evidence traceable to URL |
| 6 | Verification | Deterministic verdicts + conflicts | Unit-tested verdict matrix |
| 7 | Graph + radar | Interactive evidence workspaces | Data matches stored job |
| 8 | Reports | Auditable proof report | Export includes limitations + sources |
| 9 | Security/QA | Hardening and tests | No critical open issue |
| 10 | Packaging | Runnable handoff + demo | Clean install to demo journey |

Dependencies: 2 and 3 depend on 1; 4 depends on 3; 5 depends on 4; 6 depends on 5; 7 and 8 depend on
6; 9 spans 2–8; 10 depends on all.

Stop conditions: each phase ends when its gate passes or a documented blocker is recorded in
`BRAIN/HANDOFF.md`.
