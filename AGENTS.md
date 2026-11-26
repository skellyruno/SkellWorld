# SKELLY — MASTER DEVELOPMENT INSTRUCTIONS 🩻

> Shared development standards for the Skelly ecosystem: audio plugins, SkellCore, SkellWorld, SkellForge, SkellyHub, websites, and tools.
>
> These are ecosystem-wide baseline rules. Follow more specific repository-level requirements where applicable. Do not delete or overwrite existing project-specific `AGENTS.md` files. To make these rules automatically discoverable by coding agents in another repository, place a copy or a repository-local reference there; a file in SkellWorld alone is **not automatically inherited** by other GitHub repositories.

## 1. Development & Autonomy

- When I say "keep improving," work through the next meaningful priorities instead of stopping after one minor change.
- Fix existing bugs before adding unrelated features.
- Prefer coordinated milestone batches over tiny incremental edits across ALL Skelly projects. In each pass, audit the real baseline, address several related high-impact issues across the relevant subsystems, and batch them into a coherent implementation with regression coverage and exact-commit verification. Avoid unrelated scope creep, risky compatibility changes, repeated cosmetic-only commits, and superseding a useful validation run before its evidence can be inspected. If a dependency blocks validation, identify the blocker and explicitly separate completed work from unverified work.
- Treat broad instructions to improve, polish, or continue as authority to independently plan and execute a comprehensive, evidence-driven milestone, not a request for a sequence of tiny cosmetic edits. Inspect the exact current output and any supplied references, enumerate every material defect across the whole product, resolve root causes in one coherent batch, and verify against the reference with actual builds/tests/captures. Where the available session and tools permit, repeat inspection and correction without waiting for the owner to say 'keep going' again. Use existing assets and shared components before reinventing them. Do not sacrifice approved behavior, compatibility, safety, or verified evidence for speed or change volume.
- Make reasonable technical decisions without repeatedly asking for permission.
- Prioritize working software over lengthy explanations or unnecessary planning.
- Never claim asynchronous development is happening unless a scheduled automation is actually running.
- Continue the build → test → inspect → fix cycle within the available session.

## 2. GitHub & Workflow Efficiency

- Batch related code changes into fewer logical commits. Avoid triggering CI after every minor edit.
- Configure GitHub Actions to cancel superseded pull-request runs automatically.
- Keep only the latest relevant PR checks active whenever possible.
- Never automatically cancel production, release, main-branch, or manually triggered builds.
- Preserve successful work and avoid unnecessary force pushes.
- Use feature branches and draft PRs for unfinished development.
- Never merge unverified changes into main.
- Resolve merge conflicts carefully without discarding existing functionality.
- Avoid duplicate workflows, repeated builds, and unnecessary CI resource usage.
- Keep PR descriptions, changelogs, and development notes updated.

## 3. Testing & Verification

- Run actual builds, tests, and UI checks after meaningful batches of changes.
- Fix errors and warnings at their root cause; never hide, silence, bypass, or ignore them.
- Add regression tests for significant bug fixes.
- Never claim something works merely because code was written or compiled.
- Clearly distinguish implemented, compiled, tested, failed, blocked, and unverified work.
- Verify the exact commit associated with each build or test result.
- Never invent successful builds, screenshots, benchmarks, or test outcomes.
- If verification is unavailable, explain exactly what remains unverified.

## 4. Audio DSP & Sound Quality

- Prioritize genuine sound quality for audio plugins.
- Test DSP using actual audio recordings when available.
- Compare reference sounds using the same source audio, synchronized A/B playback, loudness matching, and objective measurements.
- Verify CPU usage, latency, clipping, true peaks, NaNs, denormals, artifacts, and parameter smoothing.
- Preserve real-time audio safety: avoid allocations, locks, blocking operations, or file access on the audio thread.
- Avoid fake DSP, misleading processing claims, and decorative controls that do not affect the sound.
- Prioritize low latency without compromising stability or sound quality.
- Never claim a plugin sounds better without supporting audio verification.

## 5. UI Design & Visual Quality

- Preserve approved interfaces unless I explicitly request a redesign.
- Change only the requested elements and avoid modifying unrelated UI components.
- Prefer SkellCore shared UI components and the existing **Quick4 local renderer** for fast previews and inspections.
- Use real application screenshots to verify visual changes.
- **Mandatory screenshot → inspect → fix → rescreenshot loop:** after every meaningful UI change, open the exact latest real app/plugin screenshots yourself, visually audit for asset bleed, clipped or overlapping controls, wrong scale, misalignment, contrast, shadows, animations and broken states, and proactively fix **all visible defects** before declaring polish complete. Rebuild and re-inspect the corrected screenshots.
- Do not treat a passing build, automated geometry assertion or screenshot file's existence as proof that the UI looks correct. Report any remaining unverified visual issue explicitly.
- Never generate mockup images unless I explicitly request them.
- Inspect text alignment, clipping, spacing, contrast, knobs, meters, menus, hover states, and animation smoothness.
- Check multiple window sizes, scaling levels, and display resolutions.
- Avoid visual clutter, unnecessary labels, and redundant controls.
- Maintain Skelly branding while allowing every plugin its own recognizable identity.
- Verify that UI controls respond correctly rather than assuming they work because they render.

## 6. SkellCore & Software Architecture

- Reuse SkellCore components instead of duplicating shared functionality.
- Keep DSP, UI rendering, preset management, and platform integrations properly separated.
- Prefer efficient, maintainable solutions over unnecessary complexity.
- Avoid new dependencies unless they offer meaningful benefits.
- Preserve shared component interfaces and existing integrations.
- Improve reusable systems when doing so benefits multiple Skelly projects.

## 7. Preset & Project Compatibility

- Never break existing presets, automation IDs, saved plugin states, or FL Studio projects.
- Never rename, remove, or renumber published automation parameters without an explicit, tested migration strategy.
- Test preset loading, saving, import/export, and recall.
- Preserve existing factory preset identities and user-created presets.
- Verify that changes to one effect do not unexpectedly alter unrelated effects.
- Prefer backward-compatible additions over destructive replacements.

## 8. Performance Optimization

- Profile CPU, memory, latency, and rendering before making optimization claims.
- Minimize unnecessary allocations, background processing, and expensive UI repaints.
- Avoid continuously redrawing static interface elements.
- Measure performance changes under repeatable test conditions.
- Document benchmark hardware, sample rate, buffer size, and test conditions.
- Address actual bottlenecks rather than making speculative optimizations.

## 9. Build, Packaging & Releases

- Never consider a plugin release-ready solely because it compiles.
- Verify Windows VST3 builds, DSP tests, UI screenshots, preset compatibility, and packaging.
- Test in FL Studio when an appropriate runtime is available.
- Keep experimental builds separate from stable releases.
- Preserve production builds and existing downloadable releases.
- Provide a direct verified VST3 download when possible.
- Identify the exact source commit for every build artifact.
- Never distribute an unverified build as a stable release.

## 10. Project Management & Priorities

- Prioritize critical functionality, sound quality, stability, and release blockers before minor cosmetic changes.
- Track completed, tested, failed, blocked, and unverified tasks separately.
- Maintain clear milestones and next actions.
- Keep the Skelly ecosystem coordinated without mixing unrelated repositories or responsibilities.
- Preserve previously approved decisions unless I explicitly change them.
- Avoid repeating work that has already been completed and verified.

## 11. Communication & Accountability

- Provide concise progress updates during substantial development tasks.
- Focus on actual results instead of repetitive status messages.
- Clearly explain blockers and their impact.
- Ask before making assumptions when missing information could cause destructive or incompatible changes.
- Do not repeatedly ask questions already answered.
- Never claim code was pushed, compiled, tested, or released unless that action actually succeeded.
- Use 🩻 in Skelly development progress updates.

## 12. Conversation Handoffs

- When a development conversation becomes too long, warn me.
- Provide a concise handoff for a new chat containing the project, repository, branch, latest commit, completed work, test results, outstanding failures, and next priorities.
- Preserve important technical decisions and approved UI designs.
- Make the handoff detailed enough to continue development without repeating earlier work.

## Offline JUCE / Quick4 continuity

- At the start of every Skelly development chat, locate and reuse the newest verified SKELLY_QUICK4_OFFLINE_KIT in ChatGPT Library (initial bundle: /SKELLY_QUICK4_OFFLINE_KIT_2026-11-26.zip) for the project's pinned JUCE version and matching offline dependencies; verify checksums, use local JUCE_PATH with FetchContent disconnected, resume existing build caches, and build/capture/inspect the actual UI. Do not refetch a cached dependency or claim native visual success before compilation and screenshot inspection. Debian 13 amd64 overlay is platform-specific; never replace system DNS or core libraries to force the build.
