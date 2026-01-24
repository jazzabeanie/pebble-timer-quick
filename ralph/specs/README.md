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

### 1. User Authentication System
**File:** [example-user-authentication.md](example-user-authentication.md)

**Keywords:** user authentication, login, registration, signup, JWT, JSON Web Token, session management, password hashing, bcrypt, security, auth middleware, identity management, user credentials, bearer token, protected routes

**Summary:** Implements secure user registration, login, and session management using JWT tokens and bcrypt password hashing.

**Status:** Not Started

**Tests:** NA

**Dependencies:** None (foundational feature)

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
