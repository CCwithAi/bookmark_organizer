# Bookmark Organizer (Project Archive)

## Project Status
This project is currently archived. It was an experimental attempt to create an AI-powered bookmark organization tool using local LLM capabilities.

## Project Overview
- **Goal**: Create a smart bookmark organizer with AI categorization
- **Stack**: Python, FastAPI, Streamlit, SQLite, Ollama
- **Status**: Development paused
- **Last Updated**: February 2024

## Components Implemented
- Browser bookmark parser
- FastAPI backend structure
- Streamlit frontend interface
- Initial AI categorization system

## Future Development Notes
For anyone interested in continuing this project, consider:
1. Implementing the revised architecture from the technical specification
2. Using a hybrid categorization approach (pattern matching + keywords + LLM)
3. Adding Floccus integration for browser synchronization
4. Improving the frontend with React/TypeScript

## Repository Structure
```
bookmark_organizer/
├── src/
│   ├── frontend/     # Streamlit UI
│   ├── backend/      # FastAPI server
│   ├── agents/       # AI categorization
│   └── parsers/      # Bookmark parsers
├── tests/            # Test suite
└── README.md         # This file
```

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Start backend: `python src/backend/app.py`
3. Start frontend: `streamlit run src/frontend/app.py`

## License
MIT License

## Contact
This project is archived. For questions about the implementation or architecture, refer to the technical documentation.
