#!/bin/bash
# deploy.sh
# Deploys claude-config (commands, agents) to ~/.claude/
# Run from claude-workshop/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/claude-config"
TARGET_DIR="$HOME/.claude"

# Validate source
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: claude-config/ not found in $SCRIPT_DIR"
  exit 1
fi

echo "Deploying claude-config → $TARGET_DIR"
echo ""

# Show diff before deploying
CHANGED=0
for src in "$SOURCE_DIR/commands/"*.md "$SOURCE_DIR/agents/"*.md; do
  [ -f "$src" ] || continue
  subpath="${src#$SOURCE_DIR/}"
  dst="$TARGET_DIR/$subpath"
  if [ -f "$dst" ] && ! diff -q "$src" "$dst" > /dev/null 2>&1; then
    echo "  ~ $subpath (changed)"
    CHANGED=1
  elif [ ! -f "$dst" ]; then
    echo "  + $subpath (new)"
    CHANGED=1
  fi
done

# Check for files to remove
for dir in commands agents; do
  [ -d "$TARGET_DIR/$dir" ] || continue
  for dst in "$TARGET_DIR/$dir/"*.md; do
    [ -f "$dst" ] || continue
    filename="$(basename "$dst")"
    if [ ! -f "$SOURCE_DIR/$dir/$filename" ]; then
      echo "  - $dir/$filename (will be removed)"
      CHANGED=1
    fi
  done
done

if [ "$CHANGED" -eq 0 ]; then
  echo "  Nothing to update."
  exit 0
fi

echo ""
read -p "Deploy? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# Deploy
mkdir -p "$TARGET_DIR/commands" "$TARGET_DIR/agents"

cp "$SOURCE_DIR/commands/"*.md "$TARGET_DIR/commands/" 2>/dev/null || true
cp "$SOURCE_DIR/agents/"*.md "$TARGET_DIR/agents/" 2>/dev/null || true

# Clean up: remove deployed files that no longer exist in source
REMOVED=0
for dir in commands agents; do
  [ -d "$TARGET_DIR/$dir" ] || continue
  for dst in "$TARGET_DIR/$dir/"*.md; do
    [ -f "$dst" ] || continue
    filename="$(basename "$dst")"
    if [ ! -f "$SOURCE_DIR/$dir/$filename" ]; then
      echo "  - $dir/$filename (removed)"
      rm "$dst"
      REMOVED=1
    fi
  done
done

echo ""
echo "Done."
