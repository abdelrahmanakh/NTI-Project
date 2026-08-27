import json
import re
from typing import Dict, Any
from app.services.generator import HybridGenerator
from app.services.retriever import Retriever
from app.services.learning_tools import LearningTools

class EvaluatorService:
    def __init__(self, generator: HybridGenerator, retriever: Retriever, tools: LearningTools):
        self.generator = generator
        self.retriever = retriever
        self.tools = tools

    def _parse_json_response(self, text: str) -> dict:
        """Safely parse JSON from LLM output, stripping markdown blocks if present."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        try:
            return json.loads(match.group(0)) if match else json.loads(text)
        except json.JSONDecodeError:
            return {}

    def run_evaluation(self, session_id: str) -> Dict[str, Any]:
        # 1. Fetch random document context from the session to evaluate
        docs = self.retriever.vector_store.collection.get(
            where={"session_id": session_id},
            limit=10
        )
        texts = docs.get("documents", [])
        if not texts:
            raise ValueError("No documents found for evaluation. Please ingest materials first.")
        
        combined_text = "\n".join(texts)[:3000]

        # 2. Generate Synthetic Q&A for RAG evaluation
        qa_prompt = f"""
        Based on the following text, generate 3 factual questions and their exact ground-truth answers.
        Return ONLY valid JSON in this format:
        [{{"question": "...", "ground_truth": "..."}}]
        Text: {combined_text}
        """
        qa_raw = self.generator.generate(
            question=qa_prompt,
            retrieved_documents=[{"text": "System Instruction: Return JSON only.", "source": "system", "page": 0}]
        )
        
        qa_pairs = []
        try:
            match = re.search(r'\[.*\]', qa_raw, re.DOTALL)
            qa_pairs = json.loads(match.group(0)) if match else json.loads(qa_raw)
        except Exception:
            qa_pairs = [{"question": "What is the main topic?", "ground_truth": "The main topic discussed in the text."}]
        
        qa_details = []
        rag_scores = {"faithfulness": 0, "answer_relevancy": 0, "context_precision": 0, "context_recall": 0}
        
        # 3. Evaluate RAG Metrics
        for pair in qa_pairs:
            q = pair.get("question", "")
            gt = pair.get("ground_truth", "")
            
            # Retrieve & Answer
            retrieved = self.retriever.retrieve(query=q, top_k=4, session_id=session_id)
            context_text = "\n".join([d.get("text", "") for d in retrieved])
            ans = self.tools.tutor(question=q, retrieved_documents=retrieved)

            eval_prompt = f"""
            Evaluate the following RAG system output.
            Question: {q}
            Ground Truth: {gt}
            Context Used: {context_text}
            Generated Answer: {ans}

            Provide scores between 0.0 and 1.0 for:
            1. faithfulness: Can the answer be entirely inferred from the context?
            2. answer_relevancy: Does the answer address the question?
            3. context_precision: Is the context useful and relevant for the question?
            4. context_recall: Does the context contain the ground truth?

            Respond ONLY with a valid JSON object matching this schema exactly. No markdown:
            {{"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0, "context_recall": 0.0}}
            """
            eval_raw = self.generator.generate(eval_prompt, [{"text": "System: JSON only.", "source": "system", "page": 0}])
            scores = self._parse_json_response(eval_raw)
            
            for k in rag_scores.keys():
                rag_scores[k] += float(scores.get(k, 0.5))

            qa_details.append({
                "question": q,
                "ground_truth": gt,
                "generated_answer": ans,
                "scores": scores
            })

        # Average RAG scores
        num_pairs = max(len(qa_pairs), 1)
        for k in rag_scores:
            rag_scores[k] = round(rag_scores[k] / num_pairs, 2)

        # 4. Evaluate Summary Feature
        retrieved_for_summary = self.retriever.retrieve(query="overview", top_k=6, session_id=session_id)
        summary_context = "\n".join([d.get("text", "") for d in retrieved_for_summary])
        summary_output = self.tools.summarize(retrieved_documents=retrieved_for_summary)

        summary_eval_prompt = f"""
        Evaluate the following summary based on the provided source material.
        Source Material: {summary_context}
        Summary: {summary_output}

        Provide scores between 0.0 and 1.0 for:
        1. faithfulness: Does the summary avoid hallucinating information outside the source?
        2. coherence: Is the summary logically organized and concise?
        3. coverage: Does the summary successfully capture the core concepts?

        Respond ONLY with a valid JSON object matching this schema exactly. No markdown:
        {{"faithfulness": 0.0, "coherence": 0.0, "coverage": 0.0}}
        """
        summary_raw = self.generator.generate(summary_eval_prompt, [{"text": "System: JSON only.", "source": "system", "page": 0}])
        summary_scores = self._parse_json_response(summary_raw)
        
        for k in ["faithfulness", "coherence", "coverage"]:
            summary_scores[k] = round(float(summary_scores.get(k, 0.5)), 2)

        return {
            "status": "success",
            "ragas_metrics": rag_scores,
            "qa_details": qa_details,
            "summary_metrics": summary_scores,
            "summary_text": summary_output
        }