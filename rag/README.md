# RAG Knowledge Base

This module implements the Retrieval-Augmented Generation (RAG) system for the NOC Copilot.

## Features

- **ChromaDB Vector Database**: Persistent storage of runbooks with vector embeddings
- **Semantic Search**: Retrieves relevant runbooks based on query similarity
- **Sample Runbooks**: 8 comprehensive telecom NOC runbooks covering common scenarios
- **Easy Integration**: Simple API for the root cause agent to retrieve context

## Usage

```python
from rag.knowledge_base import retrieve_runbooks

# Retrieve relevant runbooks for a query
context = retrieve_runbooks("BGP peer down", k=3)
```