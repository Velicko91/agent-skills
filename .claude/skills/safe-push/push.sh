#!/bin/bash
# Pushes the current branch only after it is up to date with its remote copy and has no conflict with the base.
#
# Usage: push.sh [<base>]        (run inside the repository or worktree)
#   <base>  the base branch to check for conflicts. Default: the default branch of origin.
#
# Exit codes and the first line of output:
#   0  PUSHED <branch>                 pulled what was new, no conflict, pushed
#   3  CONFLICT_REMOTE <files...>      the remote branch has commits that conflict; the merge was aborted
#   4  CONFLICT_BASE <files...>        the branch conflicts with <base>; nothing was pushed
#   5  DIRTY                           tracked files have uncommitted changes; commit or stash them first
#   2  ERROR <reason>
#
# It never rebases and never force-pushes, so it never rewrites commits that are already pushed.
set -uo pipefail

branch=$(git branch --show-current 2>/dev/null)
[ -z "$branch" ] && { echo "ERROR not on a branch (detached HEAD or not a repository)"; exit 2; }

base=${1:-}
if [ -z "$base" ]; then
  git remote set-head origin -a >/dev/null 2>&1 || true
  base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
fi
base=${base#origin/}
[ -z "$base" ] && { echo "ERROR cannot find the base branch; pass it as an argument"; exit 2; }

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "DIRTY"; git status --porcelain --untracked-files=no; exit 5
fi

git fetch -q origin "$base" || { echo "ERROR cannot fetch origin/$base"; exit 2; }
git fetch -q origin "$branch" 2>/dev/null   # absent on the first push

# 1. Take the commits that others pushed to this branch (a merge, never a rebase).
if git rev-parse --verify -q "origin/$branch" >/dev/null; then
  if [ "$(git rev-list --count "HEAD..origin/$branch")" -gt 0 ]; then
    if ! git merge -q --no-edit "origin/$branch" >/dev/null 2>&1; then
      files=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
      git merge --abort
      echo "CONFLICT_REMOTE $files"; exit 3
    fi
    echo "PULLED new commits of origin/$branch"
  fi
fi

# 2. Check for a conflict with the base, without touching the working tree.
if ! out=$(git merge-tree --write-tree --name-only "origin/$base" HEAD 2>/dev/null); then
  files=$(printf '%s\n' "$out" | sed -n '2,/^$/p' | sed '/^$/d' | tr '\n' ' ')
  echo "CONFLICT_BASE $files"; exit 4
fi

# 3. Push.
git push -q -u origin "$branch" || { echo "ERROR git push failed"; exit 2; }
echo "PUSHED $branch"
