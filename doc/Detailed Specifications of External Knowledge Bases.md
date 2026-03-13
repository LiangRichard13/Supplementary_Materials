# Detailed Specifications of External Knowledge Bases

This document outlines the construction details, preprocessing pipelines, and retrieval mechanisms for the heterogeneous knowledge bases utilized in our framework. To ensure strict data isolation and prevent data leakage, all static data-driven components are constructed exclusively from the training partitions of their respective source datasets.

## 1. Medical Cases Database

This database provides case-based evidence for preliminary logical deduction during the syndrome differentiation phase.

* **Source Data:** 1,027 structured medical records from the TCM-SD training set.
* **Feature Engineering:** The "Chief Complaint" and "Case Description" fields are concatenated as text inputs for the embedding model, while the "Confirmed Syndrome" is retained as metadata.
* **Embedding Model:** CoROM-Medical-Base.
* **Storage Solution:** Chroma vector database.
* **Retrieval Mechanism:** A hybrid retrieval system combining dense semantic vectors and sparse keyword matching. The system retrieves the top 5 candidates from each branch, applies deduplication, and outputs the final top 10 highly relevant historical cases.

**Table 1.1: Retrieval Configuration for Medical Cases**
| Parameter | Value / Method |
| :--- | :--- |
| Vector Retrieval Weight | 0.6 |
| Sparse Retrieval Weight (BM25) | 0.4 |
| Final Recall Size | 10 |

**Table 1.2: Sample Data from TCM-SD Medical Records**
| Confirmed Syndrome (确诊证候) | Chief Complaint (主诉) | Case Description (情况描述) | Four Diagnostic Summaries (四诊摘要) |
| :--- | :--- | :--- | :--- |
| 气虚不摄证 (Qi deficiency failing to control blood) | 呕血2小时 | 患者2小时前无明显诱因出现吐鲜血，色红，反酸、嗳气、烧心偶作... 舌红苔薄白，脉细弦。 | 神志清晰，精神尚可，形体适中... 舌淡红，苔白，脉细。 |

---

## 2. Taxonomy Table

This module abandons heuristic rules in favor of a data-driven, unsupervised machine learning strategy to construct a structural prior for the syndrome classification system. It helps prune the search space and mitigate model hallucinations.

* **Source Data:** Syndrome names, concept definitions, and typical clinical manifestations parsed from the TCM-SD training set.
* **Embedding Model:** CoROM-Medical-Base (used to map text into high-dimensional dense feature matrices).
* **Clustering Algorithm:** Unsupervised K-Means clustering.
* **Optimization Logic:** The algorithm iteratively optimizes the Euclidean distance from sample vectors to cluster centroids. The node with the minimum mathematical distance to the centroid is extracted as the representative syndrome for that cluster.

**Table 2.1: Taxonomy Clustering Configuration**
| Parameter | Value / Method |
| :--- | :--- |
| Number of Clusters (k) | 20 |
| Distance Metric | Euclidean Distance |
| Output | Dynamic structured classification network |

---

## 3. Entity Knowledge Graph

This graph database facilitates exact path consistency checks and ontological reasoning during the final verification and report generation phases.

* **Source Data:** 1,027 structured syndrome entries from the TCM-SD training set.
* **Ontology Architecture (Nodes):** Syndrome names, concept definitions, clinical manifestation features, related diseases, and treatment principles.
* **Storage Solution:** Neo4j graph database.
* **Vectorization Integration:** Textual clinical manifestations are converted into dense vectors using CoROM-Medical-Base and attached as vector attributes directly to the corresponding nodes to support semantic graph traversal.
* **MPPR Application:** Executes exact-match graph queries based on inferred conclusions to associate authoritative definitions and standardized treatment plans.

**Table 3.1: Sample Data from TCM-SD Syndrome Records**
| Syndrome Name (证候名称) | Clinical Manifestations (临床表现) | Definition (定义) | Treatment Methods (治疗方法) |
| :--- | :--- | :--- | :--- |
| 肺阳虚证 (Lung Yang Deficiency) | 面色晦暗或㿠白, 咳喘无力, 痰白清稀量多如泡沫状... | 是指阳气亏虚，肺失温煦，以咳嗽气喘，畏冷肢凉... 常见于哮喘、肺痿等疾病中。 | 1、肺痿 症见吐涎沫... 治宜温肺健脾... 2、哮喘 症见喘促气短... |

---

## 4. Ancient Classics Database

This database provides authoritative theoretical grounding for the Cross-Task Shared References phase of the MPPR module.

* **Source Data:** 81 canonical TCM texts sourced from the TCM-Ancient-Books repository.
* **Preprocessing Pipeline:** To bridge the semantic gap between ancient texts and modern queries, an LLM translates the raw corpus into modern standard Chinese semantic representations prior to indexing.
* **Text Segmentation:** Recursive character text splitting strategy with custom delimiters to preserve paragraph-level semantic coherence.
* **Retrieval & Refinement:** Utilizes hybrid retrieval (Vector + Sparse). The initial recalled chunks undergo a secondary reranking evaluation. An LLM is then configured as an intelligent noise filter to synthesize and summarize the key theoretical evidence from the reranked chunks.

**Table 4.1: Chunking & Retrieval Configuration for Classics**
| Parameter | Value / Method |
| :--- | :--- |
| Chunk Size | 1024 tokens |
| Overlap Window | 128 tokens |
| Vector Weight | 0.6 |
| Sparse Weight (BM25) | 0.4 |
| Reranking Model | CoROM-Medical-Base |

---

## 5. Dynamic Web Retrieval

This module addresses long-tail knowledge gaps and retrieves the most contemporary clinical guidelines outside the scope of the static pre-built databases.

* **API Integration:** Serper.
* **Functionality:** Generates real-time query statements during runtime to extract highly relevant summaries and text snippets directly from search engines.
* **Impact:** Deeply fuses static internal knowledge with dynamic external data streams, enhancing the system's robustness against rare queries and out-of-distribution clinical scenarios.
