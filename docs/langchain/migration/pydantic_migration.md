# Migrating to Pydantic 2

## Common Issues and Solutions

### 1. Replace Deprecated Imports
Replace:
```python
from langchain_core.pydantic_v1 import BaseModel
```
With:
```python
from pydantic import BaseModel
```

### 2. Passing Pydantic Objects
When using:
- BaseChatModel.bind_tools
- BaseChatModel.with_structured_output
- Tool.from_function
- StructuredTool.from_function

Ensure using Pydantic 2 objects, not Pydantic 1 objects.

### 3. Subclassing LangChain Models
Update validators:
```python
# Old (Pydantic 1)
@validator('x')

# New (Pydantic 2)
@field_validator('x')
```

### 4. Model Rebuild
When subclassing, add:
```python
YourClass.model_rebuild()
```
