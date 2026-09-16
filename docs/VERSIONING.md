# Versioning Strategy

This repository contains two distinct architectural generations of the **Fintech Guru: Buy or Wait?** affordability agent.

## V1: Frozen Hackathon Baseline
The `v1-hackathon-final` tag marks the exact state of the project as it was submitted for the HackerRank Orchestrate 24-hour hackathon (September 2026).
- **Goal:** Provide a frozen, reproducible reference for how the initial competition was solved (Rank #702 / 3,000).
- **Modification Policy:** V1 code is strictly frozen. No features, fixes, or optimizations will be backported to V1.

## V2: Production Rebuild
The `v2-production` branch represents an independent, production-oriented rewrite of the core logic.
- **Goal:** To convert the monolithic, experimental hackathon code into a clean, testable, and robust enterprise-grade system.
- **Modification Policy:** V2 evolves independently. It incorporates a formal evaluation framework, massive synthetic datasets, robust observability, scalable Docker deployments, and highly restricted/validated LLM integration.

All active development occurs on V2 branches.
