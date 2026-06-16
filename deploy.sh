#!/bin/bash
# deploy.sh
# Deploys claude-config (commands, agents) and templates to ~/.claude/
# Run from claude-workshop/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/claude-config"
TARGET_DIR="$HOME/.claude"
TEMPLATES_SOURCE_DIR="$SCRIPT_DIR/templates"
TEMPLATES_TARGET_DIR="$HOME/.claude/templates"

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

# Check for files to remove in commands/agents
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

# Show diff for templates/workflow-contract/
if [ -d "$TEMPLATES_SOURCE_DIR/workflow-contract" ]; then
  while IFS= read -r -d '' src; do
    subpath="${src#$TEMPLATES_SOURCE_DIR/}"
    dst="$TEMPLATES_TARGET_DIR/${subpath#workflow-contract/}"
    dst_full="$TEMPLATES_TARGET_DIR/$subpath"
    if [ -f "$dst_full" ] && ! diff -q "$src" "$dst_full" > /dev/null 2>&1; then
      echo "  ~ templates/$subpath (changed)"
      CHANGED=1
    elif [ ! -f "$dst_full" ]; then
      echo "  + templates/$subpath (new)"
      CHANGED=1
    fi
  done < <(find "$TEMPLATES_SOURCE_DIR/workflow-contract" -type f -print0)

  # Check for templates/workflow-contract orphans
  if [ -d "$TEMPLATES_TARGET_DIR/workflow-contract" ]; then
    while IFS= read -r -d '' dst; do
      rel="${dst#$TEMPLATES_TARGET_DIR/workflow-contract/}"
      if [ ! -f "$TEMPLATES_SOURCE_DIR/workflow-contract/$rel" ]; then
        echo "  - templates/workflow-contract/$rel (will be removed)"
        CHANGED=1
      fi
    done < <(find "$TEMPLATES_TARGET_DIR/workflow-contract" -type f -print0)
  fi
fi

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

# Deploy commands and agents
mkdir -p "$TARGET_DIR/commands" "$TARGET_DIR/agents"

cp "$SOURCE_DIR/commands/"*.md "$TARGET_DIR/commands/" 2>/dev/null || true
cp "$SOURCE_DIR/agents/"*.md "$TARGET_DIR/agents/" 2>/dev/null || true

# Clean up: remove deployed commands/agents that no longer exist in source
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

# Deploy templates/workflow-contract/
if [ -d "$TEMPLATES_SOURCE_DIR/workflow-contract" ]; then
  mkdir -p "$TEMPLATES_TARGET_DIR/workflow-contract"
  # Copy entire workflow-contract tree preserving permissions (+x on shell scripts)
  cp -rp "$TEMPLATES_SOURCE_DIR/workflow-contract/." "$TEMPLATES_TARGET_DIR/workflow-contract/"

  # Ensure runner scripts are executable
  find "$TEMPLATES_TARGET_DIR/workflow-contract/runners" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

  # Orphan cleanup: remove target files not present in source
  while IFS= read -r -d '' dst; do
    rel="${dst#$TEMPLATES_TARGET_DIR/workflow-contract/}"
    if [ ! -f "$TEMPLATES_SOURCE_DIR/workflow-contract/$rel" ]; then
      echo "  - templates/workflow-contract/$rel (removed)"
      rm "$dst"
      REMOVED=1
    fi
  done < <(find "$TEMPLATES_TARGET_DIR/workflow-contract" -type f -print0)
fi

# Deploy /init-docs templates → ~/.claude/templates/project-setup/docs/
# (resolution tier 3 for the /init-docs command)
if [ -d "$TEMPLATES_SOURCE_DIR/project-setup/docs" ]; then
  mkdir -p "$TEMPLATES_TARGET_DIR/project-setup/docs"
  cp -p "$TEMPLATES_SOURCE_DIR/project-setup/docs/"* "$TEMPLATES_TARGET_DIR/project-setup/docs/" 2>/dev/null || true
fi

echo ""
echo "Done."
