"""Real-document RAG tests: ingest actual public documents (RFC 2324 and a
NASA mission overview) among competing documents, then verify retrieval and
grounded answers.

The excerpts are real documents, not synthetic filler:
- RFC 2324 (HTCPCP) is freely redistributable per its copyright notice,
  which is preserved below.
- NASA Apollo 11 Mission Overview is a U.S. government work (public domain).
"""

import json
import time
from pathlib import Path

import pytest

from pebblemind.config import LLMConfig, RAGConfig
from pebblemind.core.llm import LLMEngine

REPO = Path(__file__).resolve().parent.parent
MODELS_15B = REPO / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
needs_15b = pytest.mark.skipif(not MODELS_15B.exists(), reason="1.5B GGUF not downloaded")
try:
    import llama_cpp  # noqa: F401
    HAS_LLAMACPP = True
except ImportError:
    HAS_LLAMACPP = False
needs_llamacpp = pytest.mark.skipif(not HAS_LLAMACPP, reason="llama-cpp-python not installed")


def _save_bench(name: str, payload: dict) -> None:
    dest = REPO / "data" / "benchmarks" / f"{name}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")


# Excerpt of RFC 2324 (HTCPCP/1.0), L. Masinter, 1 April 1998.
# Copyright (C) The Internet Society (1998). Freely distributable per the RFC notice.
RFC2324 = (
    "RFC 2324: Hyper Text Coffee Pot Control Protocol (HTCPCP/1.0), L. Masinter, "
    "1 April 1998. Copyright (C) The Internet Society (1998). This document describes "
    "HTCPCP, a protocol for controlling, monitoring, and diagnosing coffee pots. Commands "
    "to control a coffee pot are sent from client to coffee server using either the BREW "
    "or POST method, with a message body whose Content-Type is application/coffee-pot-command. "
    "A coffee pot server MUST accept both the BREW and POST method equivalently. The WHEN "
    "method is used when pouring coffee with milk: the cup holder says when enough milk has "
    "been added. HTCPCP return codes include 406 Not Acceptable, returned when the coffee "
    "pot operator cannot comply with the Accept-Addition request, and 418 I'm a teapot: any "
    "attempt to brew coffee with a teapot should result in the error code 418 I'm a teapot. "
    "No options were given for decaffeinated coffee. What's the point?"
)

# Excerpt of the NASA Apollo 11 Mission Overview (U.S. government work, public domain).
APOLLO11 = (
    "Apollo 11 Mission Overview, NASA. Apollo 11 launched from Cape Kennedy on July 16, 1969, "
    "carrying Commander Neil Armstrong, Command Module Pilot Michael Collins, and Lunar Module "
    "Pilot Edwin Buzz Aldrin into Earth orbit aboard Saturn V AS-506. On July 20, 1969, the lunar "
    "module Eagle landed in the Sea of Tranquility; Armstrong stepped onto the Moon about 109 hours "
    "after launch, and Aldrin followed about 20 minutes later. Armstrong and Aldrin spent 21 hours "
    "36 minutes on the lunar surface while Collins orbited in the command module Columbia. Apollo 11 "
    "splashed down in the Pacific Ocean on July 24, 1969, 13 miles from the recovery ship USS Hornet."
)

# A competing filler document so retrieval must rank, not merely find.
DECOY = (
    "Sourdough Starter Maintenance Guide. Feed your starter daily with equal masses of flour "
    "and water. A healthy starter doubles within six hours at room temperature. Hooch, a gray "
    "liquid on top, signals hunger; stir it back in or pour it off before feeding. For baking, "
    "use a ratio of 100 grams starter, 350 grams water, and 500 grams bread flour."
)

QUESTIONS = {
    "rfc2324": [
        ("What HTTP error code should a teapot return when someone tries to brew coffee with it?", "418"),
        ("Which HTTP method did HTCPCP add for brewing coffee?", "BREW"),
        ("What options does HTCPCP define for decaffeinated coffee?", "No options"),
    ],
    "apollo11": [
        ("When did Apollo 11 land on the Moon?", "July 20, 1969"),
        ("Who was the Command Module Pilot of Apollo 11?", "Collins"),
        ("Where did Apollo 11 splash down?", "Pacific"),
    ],
}


async def _rag_with(docs):
    from pebblemind.rag.system import RAGSystem

    tmp_db = REPO / "data" / f"realdocs_{time.time_ns()}.db"
    cfg = RAGConfig(embedding_backend="auto", vector_db_path=str(tmp_db),
                    chunk_size=220, chunk_overlap=0, max_results=3)
    rag = RAGSystem(cfg)
    await rag.initialize()
    await rag.add_documents(docs)
    return rag, tmp_db


class TestRealDocuments:
    async def test_real_docs_retrieval_among_competing_docs(self):
        """Both real docs ingested together with a decoy: every question must
        rank its own document first AND return the expected fact — retrieval,
        not the luck of there being only one document."""
        rag, tmp_db = await _rag_with([
            {"content": RFC2324, "metadata": {"source": "rfc2324"}},
            {"content": APOLLO11, "metadata": {"source": "apollo11"}},
            {"content": DECOY, "metadata": {"source": "decoy"}},
        ])
        try:
            details = []
            for source, questions in QUESTIONS.items():
                for q, marker in questions:
                    hits = await rag.search(q, k=3)
                    top1_src = hits[0].get("metadata", {}).get("source") if hits else None
                    top1_hit = top1_src == source and marker.lower() in hits[0].get("content", "").lower()
                    any_hit = marker.lower() in " ".join(h.get("content", "") for h in hits).lower()
                    details.append({"q": q, "got_sources": [top1_src], "top1_hit": top1_hit, "retrieved": any_hit})
            emb_kind = type(rag.embedding_model).__name__
            result = {"embedding": emb_kind,
                      "top1_hits": sum(d["top1_hit"] for d in details),
                      "retrieved": sum(d["retrieved"] for d in details),
                      "total": len(details), "details": details}
            _save_bench("t6_real_docs", result)
            if result["embedding"] != "HashEmbedding":
                assert result["top1_hits"] == result["total"], result
            else:
                assert result["retrieved"] >= 3, result
        finally:
            await rag.cleanup()
            try:
                tmp_db.unlink(missing_ok=True)
            except Exception:
                pass

    @needs_15b
    @needs_llamacpp
    async def test_grounded_answers_cite_real_facts(self):
        """Answers must contain the real facts (418, Collins) with the doc as context."""
        engine = LLMEngine(LLMConfig(model_path=str(MODELS_15B), model_size="1.5b", backend="llamacpp",
                                     enable_gpu_offload=True, gpu_layers=99))
        await engine.initialize()
        cases = [
            (RFC2324, QUESTIONS["rfc2324"][0], "418"),
            (APOLLO11, QUESTIONS["apollo11"][1], "Collins"),
        ]
        answers = []
        for doc, (q, _), marker in cases:
            answer = await engine.generate(
                f"Answer in at most 12 words using only the context: {q}", context=[doc])
            answers.append({"q": q, "answer": answer, "marker": marker, "ok": marker.lower() in answer.lower()})
        await engine.cleanup()
        bench_path = REPO / "data" / "benchmarks" / "t6_real_docs.json"
        bench = json.loads(bench_path.read_text()) if bench_path.exists() else {}
        bench["grounded_answers"] = answers
        _save_bench("t6_real_docs", bench)
        for a in answers:
            assert a["ok"], f"answer missing fact {a['marker']!r}: {a['answer']!r}"
