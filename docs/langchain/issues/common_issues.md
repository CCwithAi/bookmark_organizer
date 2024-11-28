# Common Issues in LangChain 0.3

## Pydantic Migration Issues
1. Using deprecated `langchain_core.pydantic_v1` namespace
2. Mixing Pydantic 1 and 2 objects in APIs
3. Outdated validator decorators in subclassed models
4. Missing model_rebuild() calls

## Version Compatibility
- Python 3.8 no longer supported
- Pydantic 1.x no longer supported
- Some packages require specific version constraints

## CLI Migration Tool
```bash
# Installation
pip install -U langchain-cli

# Usage
langchain-cli migrate --help [path to code]
langchain-cli migrate [path to code]

# Preview Changes
langchain-cli migrate --diff [path to code]

# Interactive Mode
langchain-cli migrate --interactive [path to code]
```
