# Experimental Setup Details

## 1. Syndrome Differentiation

### 1.1 Evaluation Benchmarks

**TCM-SD**
To rigorously assess the performance of the Syndrome Differentiation Agent within a high-dimensional, open-ended classification setting, we utilize the TCM-SD benchmark. A representative test set comprising 1,000 instances was meticulously curated from the original test split of 5,486 genuine clinical records. The primary objective is to identify the precise syndrome from a large-scale ontology encompassing 148 categories. To account for the inherent class imbalance prevalent in authentic clinical data, the evaluation employs **Weighted Precision**, **Weighted Recall**, and **Weighted F1-score** ($F1_{weighted}$). The calculation for $F1_{weighted}$ is formally defined as:

$$F1_{weighted}=\sum_{i \in \mathcal{C}}w_i\cdot\frac{2\cdot P_i\cdot R_i}{P_i+R_i}$$

where $\mathcal{C}$ denotes the complete set of syndrome classes, $w_i$ represents the sample proportion of class $i$, and $P_i$ and $R_i$ signify the precision and recall for class $i$, respectively.

**TCMEval-SDT**
To evaluate the logical reasoning and diagnostic acuity of the models, we employ TCMEval-SDT, consisting of 100 standardized multiple-choice questions sampled from the original validation and test splits. Each instance presents a detailed patient narrative for a multi-label selection task. We report **Samples-average Precision**, **Recall**, and **F1-score** ($F1_{samples}$) to measure instance-level performance:

$$F1_{samples}=\frac{1}{N}\sum_{j=1}^{N}\frac{2\cdot|Y_j\cap\hat{Y}_j|}{|Y_j|+|\hat{Y}_j|}$$

where $N$ is the total number of samples, $Y_j$ is the ground truth label set for sample $j$, and $\hat{Y}_j$ is the predicted label set. Additionally, we report **Accuracy (Exact Match)**, strict criteria where a prediction is deemed correct only if the predicted label set $\hat{Y}_j$ precisely matches the ground truth $Y_j$.

*Note: All experimental evaluations strictly isolate the test and validation sets from the training partitions, which are exclusively reserved for constructing the external knowledge bases. All datasets undergo rigorous de-identification to ensure compliance with ethical and privacy standards.*

### 1.2 Baselines

To comprehensively assess the incremental value of the proposed reflective mechanism, the system is benchmarked against diverse model architectures and paradigms, all utilizing Zero-shot Chain-of-Thought (CoT) prompting to expose explicit reasoning trajectories.

**Table 1: Overview of Baseline Configurations**

| Category | Models / Frameworks | Description |
| --- | --- | --- |
| **General LLMs** | DeepSeek-V3, Kimi-K2, Gemini-2.0-flash, GPT-4o, Claude-3.7 | State-of-the-art foundational models evaluated for generalized medical reasoning. |
| **TCM-Specific LLMs** | HuaTuoGPT-o1-7B, SunSimiao-7B, Carebot-8B | Domain-adapted models fine-tuned specifically on traditional Chinese medicine corpora. |
| **Multi-Agent Systems** | Voting (3 agents), Debate (3 agents, 2 rounds) | Collaborative frameworks designed to enhance reasoning through consensus or iterative critique. |
| **RAG Baseline** | Single-pass Retrieval-Augmented Generation | Shares the identical Medical Cases Database and Knowledge Graph with MedMirror to isolate architectural gains from knowledge augmentation. |

---

## 2. Tongue Diagnosis

The Tongue Diagnosis Agent operates via a decoupled cascaded architecture, fundamentally anchored by a front-end visual extractor. To ensure the reliability of this foundational stage, we comprehensively evaluate its fine-grained classification performance.

The evaluation utilizes a 5-class augmented dataset encompassing mirror-approximated, thin-white, white-greasy, yellow-greasy, and grey-black tongue coatings. Following rigorous de-identification and data augmentation (horizontal, vertical, and mirror flipping, alongside color jittering), the dataset is partitioned into 3,764 training, 236 validation, and 295 test images.

Crucially, our experiments contrast specialized Convolutional Neural Networks (CNNs)—including traditional residual networks (ResNet variants), scaling-efficient models (EfficientNet variants), and densely connected networks (DenseNet variants)—against contemporary General Multimodal Large Language Models (MLLMs), specifically the Qwen2.5-VL series. Performance is quantified using macro-average and weighted-average metrics to thoroughly assess the capacity of these architectures to capture critical micro-textures and distinguish homogeneous clinical sub-classes without suffering from visual semantic drift.

---

## 3. Output Quality Evaluation

### 3.1 Fact-based Consistency Analysis

To rigorously quantify the hallucination rate and logical fidelity of the generated narratives against the retrieved clinical evidence, we implement an **Atomic Statement Decomposition** approach. An LLM judge segments the generated response $R$ into discrete fact statements $S=\{s_1, s_2, \dots, s_n\}$, cross-referencing each against the retrieved context $C$ to classify them as *Supported*, *Contradicting*, or *Irrelevant*.

The **Fidelity Score** ($Score_{fid}$) measures the proportion of claims strictly grounded in the retrieved evidence:

$$Score_{fid}=\frac{N_{supported}}{N_{total}}$$

where $N_{supported}$ is the number of logically entailed statements, and $N_{total}$ is the total number of atomic statements.

The **Conflict Score** ($Score_{con}$) quantifies the presence of dangerous hallucinations or contradictions, serving as an inverse indicator of clinical safety:

$$Score_{con}=\frac{N_{contradicting}}{N_{total}}$$

### 3.2 Multi-dimensional Quality Scoring

Beyond factuality, an LLM judge evaluates the holistic quality of the outputs using a rigid 1-5 Likert Scale across three critical dimensions:

* **Clinical Sufficiency**: Assesses the comprehensiveness and safety of the medical advice. High scores denote factually accurate, exhaustive clinical coverage (including side effects and contraindications), while low scores indicate severe omissions or safety risks.
* **Task Compliance**: Measures strict adherence to user-specified constraints, including formatting requirements (e.g., JSON, list structures) and tone specifications.
* **Citation Accuracy**: Evaluates the validity and traceability of references. Maximum scores demand that all claims are anchored to the provided context and free from fabricated citations.

---

## 4. Meta-Evaluation

To validate the clinical utility and reliability of the synthesized diagnostic reports, a blind meta-evaluation was conducted by a panel of 15 domain experts (7 clinicians and 8 medical researchers). The experts independently assessed 20 representative case reports using a 5-point Likert scale (1: severely deficient; 5: excellent) across five specialized dimensions:

* **Evidence-Chain Completeness (ECC)**: The logical traceability from raw symptoms to the final syndrome differentiation.
* **Syndrome-Differentiation Sufficiency (SDS)**: The clarity and rigor demonstrated in excluding differential patterns.
* **Tongue-Image Utilization (TIU)**: The effectiveness of integrating multimodal visual data into the diagnostic narrative.
* **Treatment-Plan Comprehensiveness (TPC)**: The inclusion of highly personalized therapeutic modalities.
* **Diagnostic-Content Explainability (DCE)**: The clarity and accessibility of the plain-language interpretations provided to the patient.

