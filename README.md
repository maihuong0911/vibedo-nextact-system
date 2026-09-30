# Action Suggestion from Vietnamese Text

*A hybrid two-tier NLP approach to intent recognition and suggestion generation for workplace text.*

Graduation project · Faculty of Information Technology, Dai Nam University · 2026

---

## Overview

Workplace notes and messages in Vietnamese are informal, often mixed with English, abbreviated, or written without diacritics. This project investigates whether such text can be automatically mapped to a concrete **action intent** and answered with a **context-appropriate suggestion**.

The work addresses two problems in a single pipeline:

1. **Intent classification** of short Vietnamese text into 6 classes: *email, meeting, reminder, report, task assignment, approval*.
2. **Suggestion generation** conditioned on the predicted intent (e.g. email draft, meeting invitation, approval response).

A lightweight web application is included as a prototype to demonstrate the pipeline; it is not the focus of the research.

## Approach

```
Vietnamese text ─► Tier 1: PhoBERT classifier (intent + confidence)
                          │  confidence < 70% → rejected
                          ▼
                   Tier 2: Qwen3 with intent-specific prompts ─► 3 suggestion styles
```

**Key design choices**

- **Dataset.** No public Vietnamese dataset covers these intents, so one was built by localizing EmailSum (ACL 2021) into Vietnamese with four style variants per sentence (standard, lowercase, no diacritics, abbreviated). Final size: **4,617 samples**, split 80/10/10, verified manually on the most ambiguous label pairs.
- **Classifier selection.** Three strategies were compared: monolingual encoder (PhoBERT), multilingual encoder (XLM-RoBERTa), and a small decoder LLM fine-tuned with LoRA (Qwen3-0.6B).
- **Generator selection.** Qwen3-0.6B (local, CPU) and Qwen3-8B were compared; the 8B model was chosen for its more diverse and natural output.
- **Reliability.** A 70% confidence threshold (tuned on the validation set) and a gibberish filter reject ambiguous or meaningless input.

## Key Results

Evaluated on a held-out test set of 462 samples.

| Model | Accuracy | Macro F1 | Inference (CPU) |
|---|---|---|---|
| **PhoBERT-base (selected)** | **92%** | **93%** | ~50 ms |
| XLM-RoBERTa-base | 89% | 89% | ~55 ms |
| Qwen3-0.6B + LoRA | 87.2% | 87.4% | ~150 ms |

**Findings**

- The monolingual encoder outperforms both the multilingual encoder and the decoder-based classifier on short Vietnamese text.
- The most frequent confusion is between *task assignment* and *approval*, which share surface vocabulary and differ mainly in who performs the action.
- Style augmentation matters: training on standard text only lowers Macro F1 from 93% to 84% (ablation).

## Repository

```
backend/    FastAPI service, PhoBERT inference, LLM pipeline
frontend/   Prototype interface
model/      Fine-tuned PhoBERT and label encoder
evaluate_model.py   Classifier evaluation
```

Run the prototype: `pip install -r requirements.txt`, configure `.env` (database and LLM endpoint), then `uvicorn backend.app.main:app --port 8002`.

## Limitations

The dataset derives from English emails and may under-represent Vietnamese-specific documents; label boundaries overlap for some classes; suggestion quality was assessed qualitatively on a small sample. Multi-label classification and larger-scale human evaluation are natural next steps.

---

<div align="center">
  <p><b>Mai Huong Nguyen</b></p>
  <p>Information Technology, Dai Nam University · 2026</p>
  <p>Email: 3sevenm@gmail.com</p>
</div>
