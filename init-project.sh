#!/bin/bash
# init-project.sh
# Initialize a project's .claude/ directory with templates from claude-workshop.
#
# Usage:
#   ./init-project.sh <project-path> [preset]
#
# Presets:
#   ue-cpp     — Unreal Engine 5 C++ (guidelines + CLAUDE.md example)
#   general    — General purpose (web, backend, CLI, etc.)
#
# If no preset is given, lists available presets and prompts for selection.
#
# Examples:
#   ./init-project.sh ~/Projects/MyGame ue-cpp
#   ./init-project.sh ~/Projects/MyWebApp general
#   ./init-project.sh ~/Projects/MyGame              # interactive

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES="$SCRIPT_DIR/templates/project-setup"

# --- Validation ---

if [ -z "$1" ]; then
  echo "Usage: ./init-project.sh <project-path> [preset]"
  echo ""
  echo "Presets:"
  for dir in "$TEMPLATES"/guidelines-*/; do
    [ -d "$dir" ] || continue
    preset_name="$(basename "$dir" | sed 's/^guidelines-//')"
    file_count=$(find "$dir" -name '*.md' | wc -l | tr -d ' ')
    echo "  $preset_name  ($file_count guideline files)"
  done
  exit 1
fi

PROJECT="$1"
PRESET="$2"

if [ ! -d "$PROJECT" ]; then
  echo "Error: directory not found: $PROJECT"
  exit 1
fi

# --- Preset selection ---

available_presets=()
for dir in "$TEMPLATES"/guidelines-*/; do
  [ -d "$dir" ] || continue
  available_presets+=("$(basename "$dir" | sed 's/^guidelines-//')")
done

if [ -z "$PRESET" ]; then
  echo "Available presets:"
  for i in "${!available_presets[@]}"; do
    echo "  $((i+1)). ${available_presets[$i]}"
  done
  echo ""
  read -p "Select preset [1-${#available_presets[@]}]: " selection
  if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#available_presets[@]}" ]; then
    PRESET="${available_presets[$((selection-1))]}"
  else
    echo "Invalid selection."
    exit 1
  fi
fi

GUIDELINES_DIR="$TEMPLATES/guidelines-$PRESET"
if [ ! -d "$GUIDELINES_DIR" ]; then
  echo "Error: unknown preset '$PRESET'"
  echo "Available: ${available_presets[*]}"
  exit 1
fi

# --- Show plan ---

echo ""
echo "Project:    $PROJECT"
echo "Preset:     $PRESET"
echo "Source:     $GUIDELINES_DIR"
echo ""
echo "Will create:"
echo "  $PROJECT/.claude/rules/core.md"
for f in "$GUIDELINES_DIR"/*.md; do
  [ -f "$f" ] || continue
  echo "  $PROJECT/.claude/guidelines/$(basename "$f")"
done

# Check for CLAUDE.md example
CLAUDE_EXAMPLE=""
for example in "$TEMPLATES"/CLAUDE-"$PRESET"-example.md "$TEMPLATES"/CLAUDE-"${PRESET//-*/}"-example.md; do
  if [ -f "$example" ]; then
    CLAUDE_EXAMPLE="$example"
    break
  fi
done
if [ -n "$CLAUDE_EXAMPLE" ]; then
  echo "  $PROJECT/CLAUDE.md  (from $(basename "$CLAUDE_EXAMPLE"))"
fi

# Check for conflicts
CONFLICTS=0
if [ -f "$PROJECT/.claude/rules/core.md" ]; then
  echo ""
  echo "  ! .claude/rules/core.md already exists (will be overwritten)"
  CONFLICTS=1
fi
if [ -d "$PROJECT/.claude/guidelines" ]; then
  for f in "$GUIDELINES_DIR"/*.md; do
    [ -f "$f" ] || continue
    if [ -f "$PROJECT/.claude/guidelines/$(basename "$f")" ]; then
      echo "  ! .claude/guidelines/$(basename "$f") already exists (will be overwritten)"
      CONFLICTS=1
    fi
  done
fi
if [ -n "$CLAUDE_EXAMPLE" ] && [ -f "$PROJECT/CLAUDE.md" ]; then
  echo "  ! CLAUDE.md already exists (will skip — edit manually)"
  CLAUDE_EXAMPLE=""
fi

echo ""
read -p "Proceed? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# --- Copy ---

mkdir -p "$PROJECT/.claude/rules" "$PROJECT/.claude/guidelines"

# Core rules
cp "$TEMPLATES/rules/core.md" "$PROJECT/.claude/rules/core.md"
echo "  + .claude/rules/core.md"

# Guidelines
for f in "$GUIDELINES_DIR"/*.md; do
  [ -f "$f" ] || continue
  cp "$f" "$PROJECT/.claude/guidelines/$(basename "$f")"
  echo "  + .claude/guidelines/$(basename "$f")"
done

# CLAUDE.md example (only if not already present)
if [ -n "$CLAUDE_EXAMPLE" ]; then
  cp "$CLAUDE_EXAMPLE" "$PROJECT/CLAUDE.md"
  echo "  + CLAUDE.md"
fi

echo ""
echo "Done. Next steps:"
echo "  1. Edit $PROJECT/CLAUDE.md to match your project"
echo "  2. Review .claude/guidelines/ and adjust for your setup"
echo "  3. Commit the .claude/ directory to your project repo"
