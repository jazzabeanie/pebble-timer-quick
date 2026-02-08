#!/bin/bash

LOG_DIR="./test/functional"
LOG_PREFIX="pytest_results_"
MAX_LOG_FILES=1
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
pytest -v --platform=basalt ${LOG_DIR} > "${LOG_FILE}" 2>&1

# Check if pytest ran successfully
if [ $? -eq 0 ]; then
    echo "Pytest run completed successfully."
else
    echo "Pytest run failed. Check ${LOG_FILE} for details."
fi

# Clean up old log files
echo "Cleaning up old log files in ${LOG_DIR}..."
find "${LOG_DIR}" -name "${LOG_PREFIX}*.log" -type f | sort -r | sed -n "$((MAX_LOG_FILES + 1)),\$p" | xargs -r rm
echo "Keeping the most recent ${MAX_LOG_FILES} log files."
