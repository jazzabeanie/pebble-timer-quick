#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop

set -e

# Help function
show_help() {
  cat << EOF
Ralph Wiggum - Long-running AI agent loop

Usage: ./ralph.sh [OPTIONS] [max_iterations]

Options:
  --tool <name>       AI tool to use: amp, claude, or gemini (default: gemini)
  --prepend <text>    Custom text to prepend to the prompt
  -h, --help          Show this help message and exit

Arguments:
  max_iterations      Maximum number of iterations to run (default: 5)

Examples:
  ./ralph.sh                              # Run with defaults (gemini, 5 iterations)
  ./ralph.sh 10                           # Run 10 iterations
  ./ralph.sh --tool claude 3              # Use claude for 3 iterations
  ./ralph.sh --prepend "Focus on tests"   # Prepend custom instruction to prompt
EOF
  exit 0
}

# Parse arguments
TOOL="claude"
MAX_ITERATIONS=5
PREPEND_TEXT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      show_help
      ;;
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    --prepend)
      PREPEND_TEXT="$2"
      shift 2
      ;;
    --prepend=*)
      PREPEND_TEXT="${1#*=}"
      shift
      ;;
    *)
      # Assume it's max_iterations if it's a number
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

# Validate tool choice
if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "gemini" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'amp', 'claude', or 'gemini'."
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
CONTEXT_FILE="$SCRIPT_DIR/context.md"

# TODO: consider implementing a separate branch per spec file as he does in https://github.com/snarktank/ralph/blob/main/ralph.sh

# Initialize context file if it doesn't exist
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "# Ralph Context" > "$CONTEXT_FILE"
  echo "Started: $(date)" >> "$CONTEXT_FILE"
  echo "---" >> "$CONTEXT_FILE"
fi

echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Run the selected tool with the ralph prompt
  # Prompt now consists of optional prepend text + prompt.txt + context.md + all .md files in the specs directory
  FULL_PROMPT=""
  if [[ -n "$PREPEND_TEXT" ]]; then
    FULL_PROMPT="$PREPEND_TEXT

"
  fi
  FULL_PROMPT="${FULL_PROMPT}Project root: $PROJECT_ROOT

$(cat "$SCRIPT_DIR/prompt.txt" 2>/dev/null)"
  
  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(echo "$FULL_PROMPT" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "gemini" ]]; then
    OUTPUT=$(echo "$FULL_PROMPT" | gemini --yolo 2>&1 | tee /dev/stderr) || true
  else
    # Claude Code: use --dangerously-skip-permissions for autonomous operation, --print for output
    OUTPUT=$(echo "$FULL_PROMPT" | claude --dangerously-skip-permissions --print 2>&1 | tee /dev/stderr) || true
  fi
  
  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi
  
  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $CONTEXT_FILE for status."
exit 1

