# MedMirror: Towards More Reliable Diagnosis in Traditional Chinese Medicine via Reflexive Interaction and Multi-Agent Collaboration

> **Note to Reviewers**: This repository contains the reference implementation and associated artifacts for the anonymous submission *MedMirror*. To preserve the double-blind review process, all author identities, institutional affiliations, and identifiable paths have been redacted.

## Overview

Despite advancements in specialized Large Language Models (LLMs) for healthcare, existing systems often struggle with modal inflexibility, premature diagnostic inferences (hallucinations) due to sparse user input, and a lack of interpretable reasoning. 

**MedMirror** addresses these structural mismatches by transitioning from a "fast-thinking" generative paradigm to a "slow-thinking," reflexive architecture. This repository provides the codebase for our dual-loop collaborative framework, encompassing:

1. **User-Centric Reflexive Diagnostic Interaction**: Featuring a multimodal Tongue Diagnosis Agent and the Reflexive Evidence-Aware Diagnostic Loop (READ-Loop) for active clinical inquiry.
2. **Multi-Agent Collaborative Knowledge Synthesis**: Implementing Multi-Path Parallel Retrieval-Augmented Generation (MPPR) and Reflexive Argumentation & Iterative Drafting (RAID) to synthesize evidence-backed, human-readable diagnostic reports.

## Repository Organization

The repository is modularized to separate offline knowledge construction, core algorithmic prompts, and online runtime utilities. 

```text
MedMirror_Code/
├── algorithm/                  # Algorithmic documentation and paper supplements
├── doc/                        # Experimental setup and external KB specs
├── data/                       # Datasets, corpus files, and offline artifacts
├── model/                      # Local embedding and ranking model directories
├── prompts/                    # Centralized multi-agent prompt templates
├── report_example/             # Visualizations of generated diagnostic reports
├── scripts/                    # Offline pipelines for database and graph construction
└── tools/                      # Runtime modules for retrieval, ranking, and search
```

### Directory Details

- `algorithm/`: Contains theoretical formulations and architectural diagrams (e.g., `Paper_Algorithm.pdf`) that supplement the main manuscript, providing a detailed breakdown of the system's operational logic.
- `doc/`: Provides human-readable documentation that complements the paper and code:
  - `Experimental Setup Details.md`: Describes dataset splits, evaluation protocol, hyperparameters, hardware, and other experimental settings to support reproducibility.
  - `Detailed Specifications of External Knowledge Bases.md`: Specifies schema, construction pipeline, and usage patterns of external knowledge bases (e.g., Syndrome Knowledge Graph, medical case databases).
- `data/`: Hosts the raw and processed datasets utilized in our experiments.
  - Includes the VOC-formatted 5-class tongue image dataset (`tongue_5_class_dataset/`).
  - Contains the foundational corpora for knowledge graph construction (`syndrome_knowledge_graph/`), medical case vectorization (`syndrome_medical_cases/`), and hierarchical taxonomies (`syndrome_taxonomy/`).
  - *Note: Persistent artifacts like Chroma vector stores are generated and stored here during the offline build phase.*
- `model/`: Designated directory for local model weights, specifically medical-domain Chinese sentence embedding models (e.g., `nlp_corom_sentence-embedding`) and ranking models (e.g., `nlp_gte_sentence-embedding`).
- `prompts/`: The cognitive core of the multi-agent system. Prompts are organized by task domain (e.g., `mppr.py`, `raid.py`, `read_loop.py`, `tongue_diagnosis.py`), abstracting the instructional logic for content planning, targeted inquiry, and reflexive drafting.
- `report_example/`: Contains sample outputs (`1.png` - `8.png`) demonstrating the system's final multimodal diagnostic reports, highlighting clinical sufficiency and explainability.
- `scripts/`: Offline data processing pipelines designed for reproducibility:
  - `medical_cases_vector_build/`: Scripts to parse clinical jsonl records, generate LangChain `Document` objects, initialize the Chroma vector database, and serialize the BM25 index for sparse retrieval.
  - `syndrome_graph_build/`: Interfaces with Neo4j (`py2neo`) to construct the Syndrome Knowledge Graph, defining strict entity constraints and relations.
- `tools/`: Online execution modules utilized during the active consultation loop:
  - `ragRetriever.py`: Implements the hybrid semantic-sparse ensemble retrieval strategy.
  - `ranker.py`: Executes multi-stage ranking protocols, incorporating Reciprocal Rank Fusion (RRF) and model-based fine-grained sorting.
  - `serper_search.py`: External tool integration for real-time web querying, supplementing the static knowledge bases with dynamic, long-tail information.

## Mapping Code to the Paper

To assist in evaluating the methodologies proposed in the manuscript, please refer to the following code mappings:

- **Multimodal Diagnosis Framework**: Refer to `prompts/tongue_diagnosis.py` and the dataset in `data/tongue_5_class_dataset/`.
- **READ-Loop (Reflexive Evidence-Aware Diagnostic Loop)**: Refer to the interaction prompts in `prompts/read_loop.py` and the case-based retrieval functions in `tools/ragRetriever.py`.
- **MPPR (Multi-Path Parallel RAG)**: Refer to `prompts/mppr.py` for task decomposition and `tools/` for the hybrid retrieval implementation.
- **RAID (Reflexive Argumentation & Iterative Drafting)**: Refer to the Actor-Instructor collaborative logic defined in `prompts/raid.py`.

