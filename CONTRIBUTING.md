# Contributing

Thanks for your interest in contributing to the Abiqua Collection Voice RAG
system. This project is primarily a demonstration of voice AI + RAG
architecture built on a real-world domain dataset. Contributions that improve
the architecture, documentation, or educational value of the project are
welcome.

## What kinds of contributions are useful

- Bug fixes in the backend pipeline or frontend components
- Improvements to the RAG retrieval quality or prompt design
- Documentation clarifications or corrections
- Additional production callout examples in the spec docs
- Performance improvements with clear before/after measurements
- Alternative embedding or TTS provider integrations (as branches or forks)

## What this project is not accepting

- Contributions that require access to the Abiqua Collection dataset — the
  collection data is proprietary and not part of this repository
- UI redesigns that deviate significantly from the demo-first design intent
- Additional dependencies without a strong justification

## Getting started

1. Fork the repository and create a branch from `main`
2. Follow the setup instructions in README.md
3. Make your changes with clear, focused commits
4. Open a pull request with a description of what you changed and why

## Code style

**Backend (Python)**
- Follow PEP 8
- Type hints on all function signatures
- Docstrings on public functions
- No secrets or API keys in source — environment variables only

**Frontend (TypeScript)**
- Strict TypeScript — no `any` types
- Component props typed with interfaces in `src/types/`
- Tailwind for all styling — no inline styles, no CSS modules
- No new dependencies without discussion in an issue first

## Commit messages

Use conventional commit format:

```
feat: add serial number pre-filter to Atlas retrieval
fix: handle empty image_refs array in ImageGallery
docs: clarify embedding dimension verification step
chore: update LlamaIndex to 0.11.x
```

## Opening issues

If you find a bug or have a question, open a GitHub issue with:
- A clear description of the problem or question
- Steps to reproduce (for bugs)
- Your environment (OS, Python version, Node version)
- Relevant error output

## Questions about the architecture

Architecture questions are welcome as GitHub Discussions. The spec documents
in `/docs/specs/` are the authoritative reference for intended behavior — if
something in the code diverges from the spec, that is likely a bug.
