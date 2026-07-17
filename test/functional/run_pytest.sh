#!/bin/bash

LOG_DIR="./test/functional"
LOG_PREFIX="pytest_results_"
MAX_LOG_FILES=5
CONDA_ENV_PATH="/home/jared/Workspace/pebble-timer-quick/conda-env" # Absolute path

# Create a timestamp for the log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/${LOG_PREFIX}${TIMESTAMP}.log"

echo "Running pytest and saving output to ${LOG_FILE}"

# Activate the conda environment
# Conda init sets up functions like 'conda activate'
# If 'conda activate' is not available, try sourcing activate script directly
if [ -f "${CONDA_ENV_PATH}/bin/activate" ]; then
    source "${CONDA_ENV_PATH}/bin/activate"
elif [ -f "$(conda info --base)/etc/profile.d/conda.sh" ]; then
    . "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_PATH}"
else
    echo "Warning: Could not find conda activate script or conda installation."
    echo "Attempting to run pytest without activating environment."
fi

# Run pytest and redirect output to the log file
# After activating the environment, pytest should be directly in PATH
# Use PIPESTATUS to read pytest's exit code, not grep's (grep is last in the pipe).
pytest -v --platform=basalt ${LOG_DIR} 2>&1 | tee "${LOG_FILE}" | grep '%'
PYTEST_STATUS=${PIPESTATUS[0]}

# Check if pytest ran successfully
if [ "${PYTEST_STATUS}" -eq 0 ]; then
    echo "Pytest run completed successfully."
else
    echo "Pytest run failed (exit ${PYTEST_STATUS}). Check ${LOG_FILE} for details."
fi

# Surface any reruns. Tests marked @pytest.mark.flaky auto-retry on failure, so
# a green run can still hide an intermittent bug. A test that reruns *often* (vs
# a one-off load blip) is a real-bug suspect worth investigating, not ignoring.
RERUN_COUNT=$(grep -c 'RERUN' "${LOG_FILE}" 2>/dev/null || echo 0)
if [ "${RERUN_COUNT}" -gt 0 ]; then
    echo "NOTE: ${RERUN_COUNT} test rerun(s) occurred (flaky-marked tests that failed then retried):"
    grep 'RERUN' "${LOG_FILE}" | sed 's/^/  /'
    echo "  Investigate any test that reruns repeatedly across runs."
fi

# Clean up old log files, keeping the most recent ${MAX_LOG_FILES}.
# Sort by modification time (newest first) rather than by filename: name-based
# sorting misranks logs whose names don't share the timestamp layout (e.g. an
# older "pytest_results_subset_*.log" sorts above the newest run and survives
# while the run we just wrote gets deleted).
echo "Cleaning up old log files in ${LOG_DIR}..."
find "${LOG_DIR}" -maxdepth 1 -name "${LOG_PREFIX}*.log" -type f -printf '%T@ %p\n' \
    | sort -rn \
    | sed -n "$((MAX_LOG_FILES + 1)),\$p" \
    | cut -d' ' -f2- \
    | xargs -r rm
echo "Keeping the most recent ${MAX_LOG_FILES} log files."
