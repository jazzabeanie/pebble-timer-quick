# Specifications Lookup Table

## About This Folder
This folder contains detailed specification files that define the requirements for each feature or module in the project. 

**Purpose of Spec Files:**
Specification files are the **"pin" that prevents context rot**. They don't tell the AI how to code; they tell the AI **what the requirements are** so the AI can check its own work against a clear definition of "done."

Each spec file should:
- Define clear, testable requirements
- Specify API contracts and data structures  
- List dependencies on other specs
- Include a Progress section for tracking implementation status
- Be updated if implementation reveals missing or incorrect details

**For AI Agents:**
This README acts as a **lookup table** for AI search tools. Use the generative keywords to find relevant specs, then navigate to the specific .md file using the provided link. The one-sentence summary helps you quickly determine if you're looking at the right specification before committing to read the entire document. Always read the complete spec file before beginning implementation.

---

## Specification Index

### 1. Testing Framework
**File:** [testing-framework.md](testing-framework.md)

**Keywords:** testing, unit tests, integration tests, cmocka, pebble emulator, test framework, test coverage, timer tests

**Summary:** Defines the requirements for a test framework and initial set of tests for the application. Includes four unit tests for timer.c.

**Status:** Completed

**Tests:** Passing

**Dependencies:** cmocka (local copy in vendor/cmocka_install/)

---

### 2. Extended Timer Tests
**File:** [timer-extended-tests.md](timer-extended-tests.md)

**Keywords:** timer, unit tests, cmocka, timer_is_chrono, timer_is_vibrating, timer_rewind, timer_restart, timer_check_elapsed, timer_get_time_parts, timer_increment_chrono, sub-minute timer, stopwatch, chrono mode

**Summary:** Defines 11 additional unit tests for timer.c to improve coverage of chrono mode, vibration logic, restart/rewind, and sub-minute timer edge cases.

**Status:** Not Started

**Tests:** NA

**Dependencies:** testing-framework (spec #1)

---

## Adding New Specifications

When creating a new spec file:
1. Create a descriptive markdown file in this directory (e.g., `payment-processing.md`)
2. Add an entry to this README following the format above
3. Include generous keywords for searchability
4. Link to the file using relative paths
5. Set initial status to "Not Started"
6. Document any dependencies on other specs

## Status Definitions
- **Not Started**: Spec is documented but implementation hasn't begun
- **In Progress**: Active development is underway
- **Completed**: All requirements implemented and tests passing
- **Blocked**: Cannot proceed due to dependencies or external factors

## Test Status Definitions
- **NA**: No tests exist yet or are needed
- **Failing**: Tests exist but are not all passing
- **Passing**: All relevant tests are passing
