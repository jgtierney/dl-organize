# Session Start Guide

**Purpose**: Commands to run at the start of each work session to ensure you're synced with the remote repository and in the correct environment.

---

## 🚀 Quick Start (Recommended)

Simply run the startup script:

```bash
source ~/start-file-organizer.sh
```

This script will:
- Navigate to `/home/john/file-organizer`
- Check your current git status
- Fetch latest changes from remote
- Warn if you're behind remote
- Offer to merge automatically
- Activate the Python virtual environment
- Display project status and quick commands

---

## 📋 Manual Commands (If script unavailable)

### Option 1: Quick Sync (If everything is clean)

```bash
cd /home/john/file-organizer
source venv/bin/activate
git pull origin main
git status
```

### Option 2: Safe Sync (Checks status first)

```bash
# Navigate to project
cd /home/john/file-organizer

# Check current state
git status
git branch --show-current

# Fetch updates without modifying local files
git fetch origin

# See what's changed
git log --oneline HEAD..origin/main -5

# If behind, merge
git merge origin/main

# Activate environment
source venv/bin/activate

# Verify setup
python --version
```

### Option 3: Nuclear Option (Complete reset)

⚠️ **WARNING**: This discards ALL local changes!

```bash
cd /home/john/file-organizer
git fetch origin
git reset --hard origin/main
git clean -fd
source venv/bin/activate
```

---

## 🎯 What Each Command Does

| Command | Purpose |
|---------|---------|
| `cd /home/john/file-organizer` | Navigate to project root |
| `git fetch origin` | Download remote changes (doesn't modify local) |
| `git status` | Check for local changes |
| `git pull origin main` | Fetch and merge remote changes |
| `git merge origin/main` | Merge remote changes into current branch |
| `source venv/bin/activate` | Activate Python virtual environment |
| `git log --oneline -3` | Show recent commits |

---

## 📝 Pre-Session Checklist

Before starting any work session:

- [ ] Navigate to `/home/john/file-organizer`
- [ ] Fetch latest changes: `git fetch origin`
- [ ] Check if behind: `git status`
- [ ] Merge if needed: `git merge origin/main`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Verify Python: `python --version` (should be 3.12.x)
- [ ] Review status: `cat docs/project/status.md`

---

## ⚠️ Common Issues & Solutions

### Issue: "Already on branch but commits behind"

**Solution:**
```bash
git pull origin main
```

### Issue: "Local changes would be overwritten"

**Solution A - Save changes:**
```bash
git stash                    # Save local changes
git pull origin main         # Update from remote
git stash pop                # Restore local changes
```

**Solution B - Discard changes:**
```bash
git reset --hard origin/main  # ⚠️ Loses local changes
```

### Issue: "Worktree conflict"

**Solution:**
```bash
# Always work from main directory, not worktrees
cd /home/john/file-organizer
```

### Issue: "Virtual environment not activating"

**Solution:**
```bash
# Recreate venv if corrupted
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Wrong branch"

**Solution:**
```bash
git checkout main
git pull origin main
```

---

## 🔍 Verification Commands

After setup, verify everything is correct:

```bash
# Check location
pwd
# Expected: /home/john/file-organizer

# Check branch
git branch --show-current
# Expected: main (or feature branch)

# Check Python
python --version
# Expected: Python 3.12.x

# Check venv
which python
# Expected: /home/john/file-organizer/venv/bin/python

# Check dependencies
pip list | grep -E "(unidecode|pyyaml)"
# Expected: both packages listed

# Check project status
cat docs/project/status.md | head -20
```

---

## 📂 Directory Structure Verification

Your working directory should look like this:

```
/home/john/file-organizer/
├── venv/                          # Virtual environment
├── src/file_organizer/            # Source code
├── docs/                          # Documentation
├── tools/                         # Test tools
├── tests/                         # Test files
├── docs/project/status.md         # Quick status
├── ONBOARDING_COMPLETE.md         # Session summary
├── AGENT_ONBOARDING_GUIDE.md      # Agent onboarding
├── SESSION_START_GUIDE.md         # This file
├── README.md                      # Project overview
├── requirements.txt               # Dependencies
└── setup.py                       # Package config
```

---

## 🤖 For AI Agents

When starting a new agent session, have the user run:

```bash
source ~/start-file-organizer.sh
```

Then provide you with:
- Current branch output
- Latest commit hash
- Any warnings from the script

Attach these files for context:
- `docs/project/status.md` (must have)
- `ONBOARDING_COMPLETE.md` (must have)
- Relevant stage requirements if implementing a specific stage

---

## 🎓 Understanding the Setup

### Why use the startup script?
- Ensures you're always in sync with remote
- Catches potential issues before they cause problems
- Sets up environment correctly every time
- Provides useful context about project state

### Why activate venv?
- Isolates project dependencies
- Ensures correct Python version (3.12.x)
- Provides required packages (unidecode, pyyaml)

### Why fetch before pulling?
- `git fetch` is safe (doesn't modify local files)
- Lets you see what changed before merging
- Prevents surprise conflicts

---

## 📊 Expected Output

When you run `source ~/start-file-organizer.sh`, you should see:

```
=== File Organizer Session Setup ===

✓ Changed to: /home/john/file-organizer

Current branch: main
Latest local commit: 3662450 Add onboarding completion summary

Fetching from remote...
✓ Up to date with origin/main

✓ Virtual environment activated (Python 3.12.3)

Key dependencies:
PyYAML==6.0.3
Unidecode==1.3.8

=== Project Status ===
Stages 1-2: Complete (Production Ready)
Stage 3: Requirements Complete (Ready for Implementation)
Stage 4: Planning Phase

=== Quick Commands ===
  Run built-in tests:
    python src/file_organizer/filename_cleaner.py

  Generate test data:
    python tools/generate_test_data.py --size small --output /tmp/test_small

  Run file organizer (dry-run):
    python -m file_organizer -if /path/to/directory

=== Ready to work! ===
```

---

## 🔄 Session End

At the end of your session:

```bash
# Commit any changes
git add .
git commit -m "Description of changes"

# Push to remote
git push origin main

# Deactivate venv
deactivate
```

---

## 📞 Quick Reference Card

**Start session:**
```bash
source ~/start-file-organizer.sh
```

**Check status:**
```bash
git status
cat docs/project/status.md
```

**Run tests:**
```bash
python src/file_organizer/filename_cleaner.py
```

**Generate test data:**
```bash
python tools/generate_test_data.py --size small --output /tmp/test
```

**Run organizer:**
```bash
python -m file_organizer -if /path/to/dir
```

---

**Last Updated**: November 10, 2025  
**Script Location**: `~/start-file-organizer.sh`  
**Project Location**: `/home/john/file-organizer`

