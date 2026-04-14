# /hard-gate — Install enforcement hard gate

Load and follow the hard-gate-installer skill at ~/.claude/skills/hard-gate-installer/SKILL.md.

Target: $ARGUMENTS

If no target was specified, run Step 0 (discovery) from the skill to show what's installed and ask which target to gate.

If a target was specified, skip discovery and proceed directly to Step 1 (classification) with that target.

CRITICAL: All hook scripts and hook wiring go in PROJECT-LEVEL `.claude/` (not `~/.claude/`). User-level hooks do not fire in Cowork. See the COWORK COMPATIBILITY section in the skill.

This is an installation task. Do not analyze, plan, or describe what you will do. Follow the skill's protocol step by step: discover → classify → extract parameters → back up → write all 7 artifacts → verify → behavioral test → report. Every step produces a file or config edit. No step produces only prose.
