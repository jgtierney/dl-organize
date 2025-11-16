# Agent Onboarding Guide

**Purpose**: How to quickly onboard AI agents to the File Organizer project with proper context.

---

## 📋 Recommended Onboarding Prompt

```
I'm working on the File Organizer project (Python CLI for organizing 100k-500k files).

Please review the attached documentation to understand:
- Current project status (what's complete, what's next)
- Architecture and design decisions
- Testing approach and results
- Next steps and priorities

Key context:
- Working directory: /home/john/file-organizer
- Virtual environment: venv/ (use as needed)
- Git repo: git@github.com:jgtierney/dl-organize.git
- System: Linux, Python 3.12, 32GB RAM

After reviewing, let me know you're ready and I'll provide my task.
```

---

## 📎 Essential Files to Attach (in priority order)

### **Tier 1: Must Attach (Quick Context)**

1. **`docs/project/status.md`** - Single-page overview of everything
   - Current stage status
   - File locations
   - Quick commands
   - Performance metrics

2. **`ONBOARDING_COMPLETE.md`** - Comprehensive session summary
   - What's been done
   - Current state
   - Next steps
   - All recent work

### **Tier 2: For Specific Tasks**

**If implementing Stage 1:**
- `docs/stages/stage1_requirements.md` (505 lines)

**If implementing Stage 2:**
- `docs/stages/stage2_requirements.md` (580 lines)

**If implementing Stage 3:**
- `docs/stages/stage3_requirements.md` (1,400+ lines)

**If understanding design:**
- `docs/project/design_decisions.md` (29 decisions with rationale)

**If understanding the big picture:**
- `README.md` (project overview)
- `docs/project/project-phases.md` (full roadmap)

### **Tier 3: Reference (mention, don't always attach)**
- `SESSION_SUMMARY.md` - Stage 1 implementation details
- `STAGE2_TEST_RESULTS.md` - Stage 2 testing validation
- `BUG_FIXES_STAGE2.md` - Bug documentation
- `docs/onboarding.md` - Contributor guide
- `docs/agent-sessions.md` - Historical context

---

## 🎯 Recommended Workflow

### For General Continuation:
```
Attach: docs/project/status.md + docs/onboarding/onboarding_complete.md
Prompt: "Review status and continue development"
```

### For Implementing Stage 3:
```
Attach: docs/project/status.md + docs/stages/stage3_requirements.md
Prompt: "Implement Stage 3 Duplicate Detection per requirements"
```

### For Bug Fixes/Testing:
```
Attach: docs/project/status.md + relevant stage requirements
Prompt: "Fix [specific issue] in Stage X"
```

### For New Contributor:
```
Attach: README.md + docs/onboarding/onboarding.md + docs/project/status.md
Prompt: "Onboard me to this project"
```

---

## 💡 Pro Tips

1. **`docs/project/status.md` is your friend** - Always attach this, it's the single-page "state of the world"

2. **`ONBOARDING_COMPLETE.md` is the context goldmine** - Has everything from this session including all decisions made

3. **Keep it focused** - Only attach docs relevant to the immediate task (avoid information overload)

4. **Mention the venv** - Always include the working directory and venv location in your prompt

5. **Be specific about the task** - After the agent reviews docs, give clear direction on what to do

---

## 📝 Example Full Onboarding Message

```
I'm working on the File Organizer project - a Python CLI for organizing large file collections (100k-500k files).

**Context:**
- Working dir: /home/john/file-organizer
- Venv: venv/ (use for all Python commands)
- Status: Stages 1-2 complete (production ready), Stage 3 requirements complete
- System: Linux, Python 3.12, 32GB RAM

**Files attached:**
- docs/project/status.md (quick reference)
- ONBOARDING_COMPLETE.md (comprehensive context)

Please review these docs, then I'll tell you what I need help with.
```

---

## 🎯 Why This Approach Works

This approach gives the agent **90% of what they need in 2 files**, with the ability to reference specific requirements as needed:

- **docs/project/status.md**: Quick reference, current state (< 5 min read)
- **ONBOARDING_COMPLETE.md**: Deep context, decisions made, complete picture (< 10 min read)
- **Stage-specific docs**: Only when implementing that specific stage

The agent can get fully onboarded in ~15 minutes and be productive immediately.

---

## 📊 File Size Reference

| File | Lines | Purpose | Read Time |
|------|-------|---------|-----------|
| docs/project/status.md | ~190 | Quick status | 2-3 min |
| ONBOARDING_COMPLETE.md | ~440 | Full context | 8-10 min |
| stage1_requirements.md | 505 | Stage 1 specs | 15-20 min |
| stage2_requirements.md | 580 | Stage 2 specs | 15-20 min |
| stage3_requirements.md | 861 | Stage 3 specs | 20-25 min |
| README.md | ~275 | Project overview | 5-8 min |

---

## 🚀 Quick Start Template

Copy and paste this template for your next agent session:

```
File Organizer project - Python CLI for organizing 100k-500k files.

Working dir: /home/john/file-organizer
Venv: venv/ (Python 3.12)

Attached: docs/project/status.md + docs/onboarding/onboarding_complete.md

Task: [YOUR TASK HERE]
```

---

**Last Updated**: November 10, 2025  
**Created By**: AI Assistant onboarding session

