# Onboarding Guide

Welcome to the File Organizer project! This guide will help you quickly understand the project structure, navigate the documentation, and start contributing.

---

## 🎯 Quick Start (5 Minutes)

### 1. Understand the Goal
The File Organizer systematically cleans and organizes large collections of files (100k-500k files) through multiple automated stages.

### 2. Read These First
1. **[README.md](../../README.md)** - Project overview and current status (5 min read)
2. **[requirements.md](../requirements/requirements.md)** - High-level requirements (10 min read)
3. **[design_decisions.md](../design/design_decisions.md)** - Why we made specific choices (20 min read)

### 3. Current Status
- ✅ **Requirements Phase**: Complete for Stages 1-2
- 🔄 **Implementation Phase**: Ready to begin
- 📋 **Planning**: Stages 3-4 are outlined

---

## 📚 Documentation Structure

### Core Documents (Read in This Order)

#### Level 1: Overview (Start Here)
- **[README.md](../../README.md)** - What the project does, quick start
- **[requirements.md](../requirements/requirements.md)** - High-level requirements, design philosophy
- **[project-phases.md](../project-phases.md)** - Roadmap, all stages explained

#### Level 2: Detailed Specifications
- **[stage1_requirements.md](../requirements/stage1_requirements.md)** (505 lines)
  - Complete specifications for filename detoxification
  - Performance targets, examples, edge cases
  - **Read this if**: Implementing Stage 1

- **[stage2_requirements.md](../requirements/stage2_requirements.md)** (580 lines)
  - Complete specifications for folder optimization
  - Configuration file format, validation logic
  - **Read this if**: Implementing Stage 2

#### Level 3: Context & History
- **[design_decisions.md](../design/design_decisions.md)** (29 decisions)
  - Every design choice with rationale
  - Alternatives considered and why they were rejected
  - **Read this if**: Understanding the "why" behind requirements

- **[agent-sessions.md](../history/agent-sessions.md)** (4 sessions)
  - Development history and context
  - Questions asked, answers received
  - **Read this if**: Continuing work from previous sessions

---

## 🗺️ Navigation Guide

### "I want to..."

#### ...understand what this project does
→ Read [README.md](../../README.md) (5 minutes)

#### ...implement Stage 1 (filename cleaning)
→ Read [stage1_requirements.md](../requirements/stage1_requirements.md) thoroughly

#### ...implement Stage 2 (folder optimization)
→ Read [stage2_requirements.md](../requirements/stage2_requirements.md) thoroughly

#### ...understand why a decision was made
→ Search [design_decisions.md](../design/design_decisions.md) for the topic

#### ...see what's planned for future stages
→ Read [project-phases.md](../project-phases.md) Stage 3+ sections

#### ...understand system requirements
→ See "Scale & System Requirements" in [requirements.md](../requirements/requirements.md)

#### ...know what work has been done
→ Read [agent-sessions.md](../history/agent-sessions.md) for session history

#### ...write tests
→ Review "Test Requirements" sections in stage1/stage2 docs

#### ...contribute code
→ Read "Contributing" section in [README.md](../../README.md)

---

## 🔑 Key Concepts

### Multi-Stage Pipeline
The application processes files through sequential stages:
1. **Stage 1**: Filename detoxification (in-place)
2. **Stage 2**: Folder optimization (in-place)
3. **Stage 3**: Duplicate detection (planned)
4. **Stage 4**: File relocation (planned)

### Scale Optimization
- **Target**: 100,000 - 500,000 files
- **Hardware**: Optimized for 32GB RAM, 16 cores
- **Strategy**: Load full tree in memory, adaptive progress

### Safety First
- **Dry-run default**: Preview before execution
- **System protection**: Blocks dangerous directories
- **Comprehensive logging**: All operations tracked

### Design Decision Numbers
Throughout the docs, you'll see "Decision 21" or "Decision 29" references. These correspond to entries in [design_decisions.md](../design/design_decisions.md) and provide rationale for specific choices.

---

## 📊 Documentation Statistics

| Document | Lines | Purpose | Priority |
|----------|-------|---------|----------|
| requirements.md | 139 | Overview | ⭐⭐⭐ Must read |
| stage1_requirements.md | 505 | Stage 1 specs | ⭐⭐⭐ Must read for Stage 1 dev |
| stage2_requirements.md | 580 | Stage 2 specs | ⭐⭐⭐ Must read for Stage 2 dev |
| design_decisions.md | 504 | Rationale | ⭐⭐ Recommended |
| project-phases.md | ~500 | Roadmap | ⭐⭐ Recommended |
| agent-sessions.md | ~300 | History | ⭐ Optional (for context) |
| onboarding.md | This file | Navigation | ⭐⭐⭐ You're reading it! |

**Total**: 2,500+ lines of comprehensive documentation

---

## 🚀 For New Developers

### Setup (10 Minutes)
```bash
# 1. Clone repository
git clone https://github.com/jgtierney/dl-organize.git
cd dl-organize

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Read documentation
cat docs/guides/onboarding.md  # You're here!
```

### Your First Contribution

#### Option A: Implement Stage 1 Component
1. Read [stage1_requirements.md](../requirements/stage1_requirements.md) completely
2. Pick a component:
   - Filename sanitization (`filename_cleaner.py`)
   - Collision detection
   - Progress tracking
   - Logging system
3. Write tests first (TDD approach)
4. Implement the component
5. Verify against requirements
6. Submit PR with reference to requirement sections

#### Option B: Write Tests
1. Review "Test Requirements" in stage1/stage2 docs
2. Create test data structures
3. Write unit tests for specified behaviors
4. Write integration tests for full stages
5. Document test coverage

#### Option C: Improve Documentation
1. Find gaps or unclear sections
2. Propose clarifications
3. Add examples or diagrams
4. Update cross-references

---

## 🤖 For AI Agents Continuing Work

### Before Starting Work
1. Read **[agent-sessions.md](../history/agent-sessions.md)** - Most recent session first
2. Review **[design_decisions.md](../design/design_decisions.md)** - Summary table
3. Check **[project-phases.md](../project-phases.md)** - Current phase status

### During Work
- Reference design decision numbers when applicable
- Note new discussions and decisions
- Track files created/modified

### After Completing Work
1. Update **[agent-sessions.md](../history/agent-sessions.md)** with your session
2. If new decisions made: Update **[design_decisions.md](../design/design_decisions.md)**
3. If status changed: Update **[project-phases.md](../project-phases.md)**
4. Commit changes with descriptive message
5. Reference commit hash in agent-sessions.md

### Session Documentation Template
See the format in [agent-sessions.md](../history/agent-sessions.md) under any session heading.

---

## 📖 Reading Strategy by Role

### Software Developer (Implementing Features)
**Priority path**:
1. README.md → Understand project
2. requirements/requirements.md → High-level context
3. requirements/stage1_requirements.md OR requirements/stage2_requirements.md → Detailed specs for your stage
4. design/design_decisions.md → Understand rationale
5. Start coding with tests

**Time investment**: 1-2 hours of reading before coding

### Technical Writer (Documentation)
**Priority path**:
1. All documentation (skim for structure)
2. design/design_decisions.md → Understand technical depth
3. Identify gaps or unclear sections
4. Propose improvements

### Project Manager / Stakeholder
**Priority path**:
1. README.md → Project overview
2. project-phases.md → Roadmap and status
3. requirements/requirements.md → High-level requirements
4. Optional: design/design_decisions.md → Technical decisions

**Time investment**: 30-60 minutes

### Quality Assurance / Tester
**Priority path**:
1. README.md → Understand what it does
2. requirements/stage1_requirements.md + requirements/stage2_requirements.md → What to test
3. Focus on "Test Requirements" sections
4. Focus on "Success Criteria" sections
5. Create test plans

---

## 💡 Understanding Design Decisions

Design decisions are numbered for easy reference. When you see "See Decision 21" in documentation, you can quickly find it in [design_decisions.md](../design/design_decisions.md).

### Key Decisions to Understand
- **Decision 21**: Adaptive progress reporting (prevents console spam)
- **Decision 29**: Large scale optimization strategy (in-memory processing)
- **Decision 26**: Target directory validation (safety)
- **Decision 6**: Hidden file deletion (cleanup philosophy)

See the [Decision Summary Table](../design/design_decisions.md#decision-summary-table) for a complete overview.

---

## 🔍 Finding Specific Information

### Search Strategies

#### Find requirements for a specific feature
1. Check stage1 or stage2 requirements.md table of contents
2. Use Ctrl+F / grep for keywords
3. Check cross-references to related sections

#### Understand why something works a certain way
1. Search [design_decisions.md](../design/design_decisions.md) for the feature
2. Read the "Reasoning" section for that decision
3. Check "Considered Options" to see alternatives

#### See what's been implemented
1. Check [project-phases.md](../project-phases.md) status table
2. Review git commit history
3. Read [agent-sessions.md](../history/agent-sessions.md) for latest work

---

## 🎓 Learning Path

### Week 1: Understanding
- Day 1: README.md, requirements/requirements.md
- Day 2: design/design_decisions.md (skim all, read key ones)
- Day 3: requirements/stage1_requirements.md (if working on Stage 1)
- Day 4: requirements/stage2_requirements.md (if working on Stage 2)
- Day 5: project-phases.md, history/agent-sessions.md (context)

### Week 2: Contributing
- Day 1-2: Set up environment, write first tests
- Day 3-4: Implement first component
- Day 5: Review, refine, submit PR

---

## 🆘 Getting Help

### Documentation Issues
If documentation is:
- Unclear: Propose clarifications
- Missing: Identify gaps and suggest additions
- Outdated: Flag for updates
- Inconsistent: Point out conflicts

### Technical Questions
1. First: Search existing documentation thoroughly
2. Check if design decision exists for the topic
3. Review agent sessions for related discussions
4. If still unclear: Ask with context of what you've read

---

## ✅ Quick Reference Checklist

Before starting work, have you:
- [ ] Read README.md
- [ ] Read requirements/requirements.md  
- [ ] Read relevant stage requirements (requirements/stage1 or requirements/stage2)
- [ ] Reviewed applicable design decisions
- [ ] Checked history/agent-sessions.md for context
- [ ] Understood the current project phase

---

## 📝 Documentation Conventions

### File Naming
- `requirements/requirements.md` - Overview and high-level
- `requirements/stageN_requirements.md` - Detailed stage-specific
- `design/design_decisions.md` - Rationale and alternatives
- `project-phases.md` - Roadmap and status
- `history/agent-sessions.md` - Development history

### Cross-References
- `[Link Text](./filename.md)` - Relative links
- `See Decision N` - Reference to design decision
- `Section X.Y.Z` - Reference to specific requirement section

### Status Indicators
- ✅ Complete
- 🔄 In Progress
- 📋 Planning
- ⏸️ On Hold
- ❌ Blocked

---

## 🎯 Success Criteria

You understand the project when you can:
1. Explain what each stage does in 1-2 sentences
2. Name 3-5 key design decisions and why they were made
3. Navigate to specific requirements without searching
4. Understand the current project status
5. Know where to look for specific information

---

## 🔗 Quick Links

- [README](../../README.md) - Project overview
- [Requirements](../requirements/requirements.md) - High-level requirements
- [Stage 1 Specs](../requirements/stage1_requirements.md) - Filename detoxification
- [Stage 2 Specs](../requirements/stage2_requirements.md) - Folder optimization
- [Design Decisions](../design/design_decisions.md) - All 29 decisions
- [Project Phases](../project-phases.md) - Roadmap
- [Agent Sessions](../history/agent-sessions.md) - Development history

---

**Welcome aboard! The documentation is comprehensive and designed to get you productive quickly. Start with the README and work your way through. Happy organizing!** 🚀

