# September 18 research and testing addendum

These notes are source-derived observations plus explicitly labeled recommendations. Public pages were read on 2026-09-18; no Hermes deployment, browser-control session, QMX test or mutation campaign was run in preparing this package. The user's custom installed skills have not been independently inspected here. Agents must re-resolve versions and installed behavior.

## Hermes reference surfaces

- General plugins: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- Native desktop: https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk
- Web dashboard: https://hermes-agent.nousresearch.com/docs/user-guide/features/extending-the-dashboard

Observed in the general guide: separate manifest/tool-schema/handler/registration responsibilities, tool and hook contributions, plugin settings/state, and public tool dispatch. Some native-manifest dependency/configuration failures are warnings rather than load blockers. Portable plugins are not a security sandbox. These are facts about the donor, not QMX policy recommendations.

Observed in the desktop guide: a public SDK exposes registered UI contributions, scoped host/backend access and cleanup. It distinguishes native-desktop, web-dashboard and Python agent plugins, despite possible combined distribution. Built-in desktop surfaces use the contribution mechanism too.

Recommendation: compare those separate surfaces to existing QMA and the proposed QMX app host. Test public-interface usability for built-in and user additions. Reuse good registration/compatibility/lifecycle patterns, but explicitly choose QMX dependency, runtime safety and permission rules rather than copying warning-and-continue or full-trust behavior. Do not rank Hermes versus VS Code as if they implement identical scopes. Inspect relevant linked memory, context, model-provider and subagent-lifecycle guides if they inform actual gaps.

## BMAD and CIS

- https://docs.bmad-method.org/plan/design-ux-and-architecture/
- https://cis-docs.bmad-method.org/how-to/design-thinking/

The public BMAD page describes a fast architecture route with assumptions and a spine focused on decisions that need coordination. CIS design thinking includes journey mapping and prototyping/test planning. Neither page establishes what the user's customized Documentation Factory skill does. Installed skills govern their actual execution; discover/read them. Use CIS for user-centered scenario exploration and technical test methods for infrastructure/lifecycle details.

## Behavior and testing

- Gherkin: https://cucumber.io/docs/gherkin/reference/
- Stateful/property tests: https://hypothesis.readthedocs.io/en/latest/stateful.html
- Mutation testing: https://mutmut.readthedocs.io/en/latest/
- Skill evaluation reference: https://github.com/edonadei/caliper

Gherkin describes scenarios using initial conditions, actions and expected observations; runnable tests require matching implementation. Hypothesis stateful testing generates action sequences over state. mutmut is Python mutation testing and currently documents a fork-capable execution environment (WSL on Windows). Those mechanisms address different questions; none certifies system-wide correctness on its own.

Recommendation: design behavior oracles first, then contract/integration, state-machine, failure-injection and mutation evidence appropriate to real code. Identify equivalent/invalid/timeout mutants and all exclusions; do not assert that a high score proves all missing behavior is covered. Use a disposable source copy for mutation diagnostics. Keep future test plans distinct from performed tests.

## Browser reconnaissance references

- LSE: https://londonstrategicedge.com/
- OpenBB documentation: https://docs.openbb.co/
- Taskade: https://www.taskade.com/
- Official browser-capability discovery starting point (redirects/versioning may change): https://developers.openai.com/codex/app/features

The separate browser assignment is an observation plan. This update did not navigate authenticated product interfaces. The agent must discover actual browser controls, use authorized pages and distinguish interaction evidence from descriptions. Published product features and accessible data are not the same as permission to download, redistribute or execute paid jobs.

## Internal interface recommendation, not adopted schema

A useful operation description may expose a versioned name, inputs, output category, declared effect, authorization/context requirements, execution placement and failure/lifecycle behavior. It may return a small typed value, an immutable artifact reference, a job handle or a stream. These are design responsibilities to resolve against existing QMX contracts, not a mandate to mint a second universal API or put HTTP on every library. The rendering and assistant surfaces should discover the same supported operation descriptions, while grants stay host-enforced.
