# System Patterns

## System Architecture
A linear LangGraph structure: A -> B -> C.

## Key Technical Decisions
- Using LangGraph for building the graph structure.
- Using an LLM for generating responses in Node B (which may include fake PHI for testing).
- Using a second LLM call for checking for PHI in Node C.

## Component Relationships
- Node A (receives user question) -> Node B (generates response which may include fake PHI) -> Node C (checks response for PHI).
