"""
AI POD Query System - Pure Semantic Search
No keywords, no hardcoded rules, just vector similarity
"""

import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq
import re
import time
from typing import Dict, List, Optional

from config import AIPodConfig


# Language Detection (Only for UI display)
def detect_language(text: str) -> str:
    """Simple Arabic detection - ONLY for UI display"""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    if arabic_pattern.search(text):
        return "ar"
    return "en"

# Query System - Pure Semantic Search
class AIPodQuerySystem:
    """Pure semantic search - NO keywords, NO hardcoded rules"""
    
    def __init__(self):
        print("🚀 Loading AI POD Query System...")
        print(f"🤖 {AIPodConfig.COMPANY_NAME} - {AIPodConfig.PROJECT_NAME}")
        print("⚡ Pure Semantic Search Mode - No keyword dependencies")

        # Check if index exists
        if not os.path.exists(AIPodConfig.FAISS_INDEX_PATH):
            raise FileNotFoundError(
                "FAISS index not found. Please run: python ingest_documents.py"
            )

        # Load FAISS index
        print("📚 Loading FAISS index...")
        self.index = faiss.read_index(AIPodConfig.FAISS_INDEX_PATH)
        
        # Load chunks
        print("📄 Loading document chunks...")
        with open(AIPodConfig.CHUNKS_PATH, "rb") as f:
            self.chunks = pickle.load(f)
        
        # Load metadata
        with open(AIPodConfig.METADATA_PATH, "rb") as f:
            self.metadata = pickle.load(f)
        
        # Load thresholds (or use defaults)
        self.thresholds = self.load_thresholds()
        
        # Load embedding model
        print("🧠 Loading embedding model...")
        self.embed_model = SentenceTransformer(AIPodConfig.EMBEDDING_MODEL)
        
        # Initialize Groq client
        self.groq_client = self.init_groq()
        
        # Print system info
        self.print_system_info()

    # -----------------------------------------------------
    def load_thresholds(self):
        """Load calibrated thresholds or use defaults"""
        try:
            if os.path.exists(AIPodConfig.THRESHOLDS_PATH):
                with open(AIPodConfig.THRESHOLDS_PATH, "rb") as f:
                    thresholds = pickle.load(f)
                print("✅ Loaded calibrated thresholds")
                return thresholds
        except Exception as e:
            print(f"⚠️ Could not load thresholds: {e}")
        
        # Default thresholds (will be overridden by calibration)
        print("⚠️ Using default thresholds")
        return {
            'high': 0.45,
            'medium': 0.30,
            'low': 0.20
        }

    # -----------------------------------------------------
    def print_system_info(self):
        """Print system information"""
        print(f"\n📊 System Information:")
        print(f"   • Total chunks: {len(self.chunks)}")
        
        # Count by language
        languages = {}
        for chunk in self.chunks[:100]:  # Sample first 100
            lang = chunk.get('metadata', {}).get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        print(f"   • Languages detected: {', '.join(languages.keys())}")
        print(f"   • Documents: {self.metadata.get('documents', ['Unknown'])[:3]}...")
        print(f"\n📊 Semantic Thresholds:")
        print(f"   • High relevance: > {self.thresholds['high']:.1%}")
        print(f"   • Medium relevance: {self.thresholds['medium']:.1%} - {self.thresholds['high']:.1%}")
        print(f"   • Low relevance: {self.thresholds['low']:.1%} - {self.thresholds['medium']:.1%}")
        print(f"   • Off-topic: < {self.thresholds['low']:.1%}")

    # -----------------------------------------------------
    def init_groq(self):
        """Initialize Groq client"""
        try:
            if not AIPodConfig.GROQ_API_KEY:
                print("⚠️ No Groq API key found")
                return None
            
            client = Groq(api_key=AIPodConfig.GROQ_API_KEY)
            
            # Test connection
            test_response = client.chat.completions.create(
                model=AIPodConfig.LLM_MODEL_FAST,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1
            )
            
            print("✅ Groq API connected")
            return client
            
        except Exception as e:
            print(f"⚠️ Groq API failed: {e}")
            return None

    # -----------------------------------------------------
    def search_semantic(self, query: str, k: int = None) -> List[Dict]:
        """Pure semantic search - NO keywords, just vector similarity"""
        if k is None:
            k = AIPodConfig.DEFAULT_SEARCH_K
        
        # Encode query
        query_embedding = self.embed_model.encode([query])
        
        # Search index
        distances, indices = self.index.search(query_embedding.astype("float32"), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= len(self.chunks):
                continue
            
            chunk = self.chunks[idx]
            
            # Convert distance to similarity score (0-1)
            similarity = 1 / (1 + distances[0][i])
            
            results.append({
                "text": chunk.get('text', ''),
                "similarity": similarity,
                "metadata": chunk.get('metadata', {}),
                "chunk_id": int(idx)
            })
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results

    # -----------------------------------------------------
    def calculate_confidence(self, context_chunks: List[Dict]) -> float:
        """Calculate confidence based ONLY on similarity scores"""
        if not context_chunks:
            return 0.0
        
        best = context_chunks[0]['similarity']
        
        # Base confidence from best match
        if best >= 0.6:
            confidence = 0.85 + (best - 0.6) * 0.5  # 0.85-0.95
        elif best >= 0.45:
            confidence = 0.70 + (best - 0.45) * 0.6  # 0.70-0.84
        elif best >= 0.30:
            confidence = 0.50 + (best - 0.30) * 0.7  # 0.50-0.69
        else:
            confidence = best * 1.2  # 0.36 max
        
        # Boost if there's a clear winner
        if len(context_chunks) > 1:
            gap = context_chunks[0]['similarity'] - context_chunks[1]['similarity']
            confidence += min(0.1, gap * 0.2)
        
        # Cap at reasonable limits
        return max(0.0, min(0.95, confidence))

    # -----------------------------------------------------
    def ask_with_groq(self, question: str, context_chunks: List[Dict]) -> str:
        """Generate answer using Groq - ONLY from provided context"""
        
        # Prepare context from documents ONLY
        context_text = "\n\n---\n\n".join([
            f"[From: {chunk['metadata'].get('file_name', 'Company Policy')}]\n{chunk['text']}"
            for chunk in context_chunks[:AIPodConfig.MAX_CHUNKS_PER_QUERY]
        ])
        
        lang = detect_language(question)
        
        if lang == 'ar':
            system_prompt = f"""أنت مساعد AI POD لشركة {AIPodConfig.COMPANY_NAME}.
مهمتك: الإجابة على أسئلة الموظفين باستخدام وثائق سياسات الشركة فقط.

قواعد صارمة:
1. استخدم ONLY المعلومات الموجودة في الوثائق أدناه
2. لا تخترع أو تضيف معلومات غير موجودة في الوثائق
3. إذا كانت الوثائق لا تحتوي على إجابة، قل ذلك بوضوح
4. اذكر اسم المستند الذي استخدمته
5. أنهِ بـ: "يرجى التحقق من الوثائق الرسمية."

الوثائق المتاحة:"""
            
            user_prompt = f"""{system_prompt}

{context_text}

سؤال الموظف:
{question}

الإجابة (باستخدام ONLY المعلومات من الوثائق أعلاه):"""
        
        else:
            system_prompt = f"""You are AI POD assistant for {AIPodConfig.COMPANY_NAME}.
Your task: Answer employee questions using ONLY company policy documents.

STRICT RULES:
1. Use ONLY information from the documents below
2. Do not invent or add information not in the documents
3. If documents don't contain the answer, say so clearly
4. Mention which document you used
5. End with: "Please verify with official documentation."

Available documents:"""
            
            user_prompt = f"""{system_prompt}

{context_text}

Employee Question:
{question}

Answer (using ONLY information from documents above):"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model=AIPodConfig.LLM_MODEL_FAST,
                messages=[
                    {"role": "system", "content": "You are a helpful policy assistant. Answer ONLY from the provided documents."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ Groq error: {e}")
            # Fallback to direct chunk response
            if context_chunks:
                return f"Based on {context_chunks[0]['metadata'].get('file_name', 'company policies')}:\n\n{context_chunks[0]['text'][:500]}"
            else:
                return "No relevant information found in company policies."

    # -----------------------------------------------------
    def ask(self, question: str) -> Dict:
        """Main method - Pure semantic search, NO keywords"""
        start_time = time.time()
        
        try:
            # Step 1: Pure semantic search
            all_results = self.search_semantic(question, k=AIPodConfig.DEFAULT_SEARCH_K)
            
            # Step 2: Check if we have ANY relevant results
            if not all_results:
                return self.no_information_response(question)
            
            best_similarity = all_results[0]['similarity']
            
            # Step 3: Decision based ONLY on similarity
            if best_similarity >= self.thresholds['high']:
                # Excellent match
                context_chunks = all_results[:AIPodConfig.TOP_K_RESULTS]
                confidence = self.calculate_confidence(context_chunks)
                
                if self.groq_client:
                    answer = self.ask_with_groq(question, context_chunks)
                    mode = "ai_enhanced"
                else:
                    answer = f"Based on company policies:\n\n{context_chunks[0]['text'][:500]}"
                    mode = "direct_match"
                
                return {
                    "answer": answer,
                    "sources": context_chunks,
                    "confidence": confidence,
                    "mode": mode,
                    "match_type": "exact_match",
                    "language": detect_language(question),
                    "response_time": time.time() - start_time
                }
                
            elif best_similarity >= self.thresholds['medium']:
                # Good match - related content
                context_chunks = all_results[:AIPodConfig.TOP_K_RESULTS]
                confidence = self.calculate_confidence(context_chunks)
                
                if self.groq_client:
                    answer = self.ask_with_groq(question, context_chunks)
                    
                    # Add context disclaimer
                    lang = detect_language(question)
                    if lang == 'ar':
                        answer += "\n\n⚠️ هذه المعلومات ذات صلة بموضوع سؤالك ولكنها قد لا تجيب عليه مباشرة."
                    else:
                        answer += "\n\n⚠️ This information is related to your question but may not directly answer it."
                    
                    mode = "ai_enhanced_related"
                else:
                    answer = f"Related information from policies:\n\n{context_chunks[0]['text'][:500]}"
                    mode = "related_match"
                
                return {
                    "answer": answer,
                    "sources": context_chunks,
                    "confidence": confidence,
                    "mode": mode,
                    "match_type": "related_match",
                    "language": detect_language(question),
                    "response_time": time.time() - start_time
                }
                
            else:
                # Low similarity - no relevant information
                return self.no_information_response(question)
                
        except Exception as e:
            print(f"❌ Error in ask(): {e}")
            import traceback
            traceback.print_exc()
            return self.error_response(question)

    # -----------------------------------------------------
    def no_information_response(self, question: str) -> Dict:
        """Return honest 'no information' response"""
        lang = detect_language(question)
        
        if lang == 'ar':
            answer = "لم يتم العثور على معلومات ذات صلة بسؤالك في سياسات الشركة الحالية."
        else:
            answer = "No relevant information found in current company policies."
        
        return {
            "answer": answer,
            "sources": [],
            "confidence": 0.0,
            "mode": "no_information",
            "match_type": "none",
            "language": lang,
            "response_time": 0.0
        }

    # -----------------------------------------------------
    def error_response(self, question: str) -> Dict:
        """Return error response"""
        lang = detect_language(question)
        
        if lang == 'ar':
            answer = "عذراً، حدث خطأ في النظام. يرجى المحاولة مرة أخرى."
        else:
            answer = "Sorry, a system error occurred. Please try again."
        
        return {
            "answer": answer,
            "sources": [],
            "confidence": 0.0,
            "mode": "error",
            "match_type": "error",
            "language": lang,
            "response_time": 0.0
        }

    # -----------------------------------------------------
    def chat(self):
        """Interactive chat interface"""
        print("\n" + "=" * 60)
        print("💬 AI POD - Pure Semantic Search Assistant")
        print("=" * 60)
        print("✓ Answers ONLY from company policies")
        print("✓ No keywords, no hardcoded rules")
        print("✓ Supports any department, any language")
        print("=" * 60)
        
        while True:
            question = input("\n❓ Question: ").strip()
            
            if question.lower() in {"quit", "exit", "q"}:
                print("👋 Goodbye")
                break
            
            if not question:
                continue
            
            result = self.ask(question)
            
            print("\n📋 Answer:")
            print("-" * 60)
            print(result["answer"])
            print("-" * 60)
            
            if result["sources"]:
                print(f"\n📊 Confidence: {result['confidence']:.1%}")
                print(f"📄 Source: {result['sources'][0]['metadata'].get('file_name', 'Unknown')}")
                print(f"🎯 Match: {result['match_type']}")
                print(f"⚡ Response: {result['response_time']:.2f}s")
            
            print()


# Main
if __name__ == "__main__":
    try:
        ai_pod = AIPodQuerySystem()
        ai_pod.chat()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("\n💡 Please run ingestion first:")
        print("   python ingest_documents.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()