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
  --sleep             Sleep 5 hours between iterations
  -h, --help          Show this help message and exit

Arguments:
  max_iterations      Maximum number of iterations to run (default: 5)

Examples:
  ./ralph.sh                              # Run with defaults (gemini, 5 iterations)
  ./ralph.sh 10                           # Run 10 iterations
  ./ralph.sh --tool claude 3              # Use claude for 3 iterations
  ./ralph.sh --prepend "Focus on tests"   # Prepend custom instruction to prompt
  ./ralph.sh --sleep 10                   # Sleep 5 hours between iterations, run 10 times
EOF
  exit 0
}

# Parse arguments
TOOL="claude"
MAX_ITERATIONS=5
PREPEND_TEXT=""
SLEEP_ENABLED=false

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
    --sleep)
      SLEEP_ENABLED=true
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

PREVIOUS_COMPLETE=false

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

  # Only add VERIFICATION REQUIREMENT if previous iteration found COMPLETE
  if [[ "$PREVIOUS_COMPLETE" == "true" ]]; then
    FULL_PROMPT="${FULL_PROMPT}

---

VERIFICATION REQUIREMENT:
Currently the phase of work is to very that the existing implementation was done properly. Verify that the specification has been fully and correctly implemented. Review the spec files in the specs/ directory against the actual implementation. Only if the spec has been properly implemented should you add <promise>VERIFIED</promise> to the end of your output."
  fi
  
  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(echo "$FULL_PROMPT" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "gemini" ]]; then
    OUTPUT=$(echo "$FULL_PROMPT" | gemini --yolo 2>&1 | tee /dev/stderr) || true
  else
    # Claude Code: use --dangerously-skip-permissions for autonomous operation, --print for output
    OUTPUT=$(echo "$FULL_PROMPT" | claude --dangerously-skip-permissions --print 2>&1 | tee /dev/stderr) || true
  fi
  
  # Check for verified signal - if spec is verified, we're done
  if echo "$OUTPUT" | grep -q "<promise>VERIFIED</promise>"; then
    echo ""
    echo "Ralph verified the spec implementation!"
    echo "Verified at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi
  
  # Check for completion signal - if tasks are complete, next iteration will require verification
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    PREVIOUS_COMPLETE=true
  fi
  
  echo "Iteration $i complete. Continuing..."
  if [[ $i -lt $MAX_ITERATIONS ]]; then
    if [[ "$SLEEP_ENABLED" == "true" ]]; then
      echo "Sleeping for 5 hours before next iteration..."
      sleep $((5 * 60 * 60))
    else
      sleep 2
    fi
  fi
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $CONTEXT_FILE for status."
exit 1

