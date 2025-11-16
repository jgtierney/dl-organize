# Move Project Directory from file-organizer to dl-organize

## Overview

Move the project directory from `/home/john/file-organizer/` to `/home/john/dl-organize/` to match the GitHub repository name. This is a straightforward directory move with minimal code changes needed.

## Analysis Results

### Current State

- **Git Remote**: Already points to `dl-organize` repository (git@github.com:jgtierney/dl-organize.git) ✅
- **README**: Already shows `cd dl-organize` in clone instructions ✅
- **Hardcoded Paths Found**: Only 1 reference in `SETUP.md` line 17: `/home/john/file-organizer`
- **CLI Command Name**: `file-organizer` (this is fine - it's the tool name, not directory name)
- **Code Paths**: No hardcoded absolute paths in source code - all paths are relative or user-provided ✅

### What Needs to Change

1. **Physical Directory Move**: Move `/home/john/file-organizer/` → `/home/john/dl-organize/`
2. **Update SETUP.md**: Change hardcoded path reference
3. **Virtual Environment**: The `venv/` directory contains absolute paths - needs to be recreated or handled carefully
4. **Build Artifacts**: `build/` directory may contain paths - can be regenerated
5. **Cache/Config**: `.file_organizer_cache/` and `.file_organizer.yaml` are relative to execution directory - no changes needed

## Implementation Steps

### Step 1: Pre-Move Preparation

- Verify no processes are using the directory
- Check for any open file handles or active operations
- Note current working directory if terminal is in project folder

### Step 2: Move the Directory

- Use `mv` command to move the entire directory: `mv /home/john/file-organizer /home/john/dl-organize`
- This preserves all file permissions, git history, and directory structure

### Step 3: Update Hardcoded Path Reference

- Update `SETUP.md` line 17: Change `/home/john/file-organizer` to `/home/john/dl-organize`

### Step 4: Handle Virtual Environment

- **Option A (Recommended)**: Delete `venv/` and recreate it after move (cleanest approach)
- **Option B**: Keep venv but user will need to recreate it (venv contains absolute paths)
- Update `SETUP.md` to reflect new path in venv creation step

### Step 5: Clean Up Build Artifacts (Optional)

- Remove `build/` directory (can be regenerated with `python setup.py build`)
- Remove `*.egg-info/` directories (can be regenerated)
- Keep `AppDir/` if needed for AppImage builds

### Step 6: Verify After Move

- Check git status (should show no changes except SETUP.md)
- Verify README clone instructions still work
- Test that `python -m src.file_organizer --version` works
- Verify no broken symlinks or references

## Files to Update

1. **SETUP.md** (line 17): Update hardcoded path from `/home/john/file-organizer` to `/home/john/dl-organize`

## Files That Don't Need Changes

- **README.md**: Already uses `dl-organize` in clone instructions
- **claude.md**: Already uses `dl-organize` in clone instructions  
- **All source code**: No hardcoded paths
- **Git config**: Already points to correct repository
- **setup.py**: Already has correct GitHub URL

## Considerations

### Virtual Environment

The `venv/` directory contains absolute paths in activation scripts and pyvenv.cfg. Best practice is to recreate it after the move:

```bash
cd /home/john/dl-organize
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Build Artifacts

Build artifacts in `build/` and `*.egg-info/` contain absolute paths but can be safely regenerated. Consider removing them before or after the move.

### Cache and Config Files

- `.file_organizer_cache/` - Relative to execution directory, no changes needed
- `.file_organizer.yaml` - Relative to execution directory, no changes needed

### Git Repository

Git will handle the move automatically - the `.git` directory contains relative paths and will work correctly in the new location.

## Risk Assessment

**Low Risk**:

- Only one hardcoded path reference found
- Git repository will work correctly after move
- Source code has no hardcoded paths
- Cache/config files are relative to execution directory

**Mitigation**:

- Virtual environment needs recreation (expected and documented)
- Build artifacts can be regenerated if needed