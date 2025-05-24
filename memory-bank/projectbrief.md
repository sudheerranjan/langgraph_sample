# LangGraph Demo - Question Answering with PHI Check

## Description
This project demonstrates a LangGraph use-case where a user question is processed through a graph composed of three nodes:
1. Node A receives a user question.
2. Node B generates a response using an LLM.
3. Node C checks the response for any Protected Health Information (PHI) and returns a "safe" response if any such content is detected.
