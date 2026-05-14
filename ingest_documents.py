"""
AI POD Document Ingestion - Optimized Multi-File Version
Pure semantic chunking with no keyword dependencies
"""

import os
import pickle
import hashlib
import datetime
import random
from typing import Dict, List
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time
import json
import PyPDF2
from config import AIPodConfig

class DocumentProcessor:
    """Process documents and build FAISS index - Pure semantic approach"""
    
    def __init__(self):
        # Create directories
        AIPodConfig.create_directories()
        
        # Load embedding model
        print("📚 Loading embedding model...")
        self.embedder = SentenceTransformer(AIPodConfig.EMBEDDING_MODEL)
        
        self.chunks: List[Dict] = []
        self.documents: List[Dict] = []
        self.total_files = 0
        
        print("✓ Document Processor initialized")
        print(f"  Source directory: {AIPodConfig.DOCUMENTS_DIR}")
        print(f"  Chunk size: {AIPodConfig.CHUNK_SIZE} chars")
        print(f"  Embedding model: {AIPodConfig.EMBEDDING_MODEL}")

    # -----------------------------------------------------
    def get_all_documents(self) -> List[str]:
        """Get all .txt and .pdf files from documents directory"""
        all_files = []
        for file in os.listdir(AIPodConfig.DOCUMENTS_DIR):
            if file.endswith('.txt') or file.endswith('.pdf'):
                full_path = os.path.join(AIPodConfig.DOCUMENTS_DIR, file)
                all_files.append(full_path)
                print(f"  📄 Found: {file}")
        
        self.total_files = len(all_files)
        return all_files

    # -----------------------------------------------------
    def extract_text_from_pdf(self, path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"  ❌ Error reading PDF {os.path.basename(path)}: {e}")
            return ""

    # -----------------------------------------------------
    def extract_text(self, path: str) -> str:
        """Read text from file based on extension"""
        if path.lower().endswith('.pdf'):
            return self.extract_text_from_pdf(path)
        else:  # .txt
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"  ❌ Error reading {os.path.basename(path)}: {e}")
                return ""

    # -----------------------------------------------------
    def split_by_language(self, text: str, filename: str = "") -> Dict[str, str]:
        """Split text into language sections - handles both marked files and separate files"""
        sections = {}
        filename_lower = filename.lower()
        
        # CASE 1: Filename indicates language (for separate PDFs)
        if 'english' in filename_lower or 'en' in filename_lower or 'eng' in filename_lower:
            print(f"  📌 Detected English from filename")
            sections["en"] = text
            return sections
        elif 'arabic' in filename_lower or 'ar' in filename_lower or 'ara' in filename_lower:
            print(f"  📌 Detected Arabic from filename")
            sections["ar"] = text
            return sections
        
        # CASE 2: Look for language markers inside the text
        en_start = text.find("=== LANGUAGE: EN ===")
        ar_start = text.find("=== LANGUAGE: AR ===")
        
        if en_start >= 0 and ar_start >= 0:
            if en_start < ar_start:
                en_content = text[en_start + 20:ar_start].strip()
                ar_content = text[ar_start + 20:].strip()
            else:
                ar_content = text[ar_start + 20:en_start].strip()
                en_content = text[en_start + 20:].strip()
            
            if en_content:
                sections["en"] = en_content
            if ar_content:
                sections["ar"] = ar_content
        elif en_start >= 0:
            sections["en"] = text[en_start + 20:].strip()
        elif ar_start >= 0:
            sections["ar"] = text[ar_start + 20:].strip()
        else:
            # CASE 3: No markers - ask user or assume
            print(f"  ⚠️ No language markers found in {filename}")
            print(f"  Assuming English (you can rename file to include 'english' or 'arabic')")
            sections["en"] = text
        
        return sections

    # -----------------------------------------------------
    def chunk_text_semantic(self, text: str, base_metadata: Dict) -> List[Dict]:
        """Semantic chunking - preserves meaning"""
        if not text.strip():
            return []
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            para_len = len(para)
            
            if para_len > AIPodConfig.CHUNK_SIZE:
                # Split long paragraphs
                sentences = para.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sentence_len = len(sentence)
                    if current_size + sentence_len > AIPodConfig.CHUNK_SIZE and current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        chunks.append(self._build_chunk(chunk_text, base_metadata))
                        current_chunk = [sentence]
                        current_size = sentence_len
                    else:
                        current_chunk.append(sentence)
                        current_size += sentence_len
            else:
                # Normal paragraph
                if current_size + para_len > AIPodConfig.CHUNK_SIZE and current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(self._build_chunk(chunk_text, base_metadata))
                    current_chunk = [para]
                    current_size = para_len
                else:
                    current_chunk.append(para)
                    current_size += para_len
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._build_chunk(chunk_text, base_metadata))
        
        return chunks

    # -----------------------------------------------------
    def _build_chunk(self, text: str, metadata: Dict) -> Dict:
        """Build a chunk with rich metadata"""
        meta = metadata.copy()
        meta.update({
            "chunk_id": len(self.chunks),
            "chunk_hash": hashlib.md5(text.encode()).hexdigest()[:8],
            "char_length": len(text),
            "word_count": len(text.split()),
            "created_at": datetime.datetime.now().isoformat()
        })
        return {"text": text, "metadata": meta}

    # -----------------------------------------------------
    def process_all_files(self) -> bool:
        """Process all files with progress tracking"""
        all_files = self.get_all_documents()
        
        if not all_files:
            print("❌ No files found in documents directory")
            return False
        
        print(f"\n📁 Found {len(all_files)} file(s)")
        
        total_chunks = 0
        start_time = time.time()
        
        for file_idx, file_path in enumerate(all_files, 1):
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            print(f"\n[{file_idx}/{len(all_files)}] 📄 Processing: {file_name}")
            
            raw_text = self.extract_text(file_path)
            if not raw_text:
                continue
            
            sections = self.split_by_language(raw_text, file_name)
            
            if not sections:
                print(f"  ⚠️ No language sections found")
                continue
            
            print(f"  ✓ Languages: {list(sections.keys())}")
            
            base_metadata = {
                "department": "Multi-Department",
                "document": file_name.replace('.txt', '').replace('.pdf', ''),
                "file_name": file_name,
                "file_type": file_ext[1:],  # txt or pdf
                "ingested_at": datetime.datetime.now().isoformat(),
                "source": "Internal Documents"
            }
            
            file_chunks = 0
            
            for lang, content in sections.items():
                if not content.strip():
                    continue
                    
                lang_metadata = base_metadata.copy()
                lang_metadata["language"] = lang
                
                lang_chunks = self.chunk_text_semantic(content, lang_metadata)
                
                if lang_chunks:
                    self.chunks.extend(lang_chunks)
                    file_chunks += len(lang_chunks)
                    print(f"    • {lang.upper()}: {len(lang_chunks)} chunks")
            
            total_chunks += file_chunks
            print(f"  ✅ Added: {file_chunks} chunks")
            
            elapsed = time.time() - start_time
            avg_time = elapsed / file_idx
            remaining = avg_time * (len(all_files) - file_idx)
            print(f"  ⏱️  Progress: {total_chunks} chunks, ~{remaining:.0f}s remaining")
        
        if total_chunks == 0:
            print("\n❌ No valid content found")
            return False
        
        elapsed_total = time.time() - start_time
        print(f"\n✅ Processing completed in {elapsed_total:.1f} seconds")
        print(f"✅ Total chunks: {total_chunks}")
        
        return True

    # -----------------------------------------------------
    def build_index(self) -> bool:
        """Build FAISS index from all chunks"""
        if not self.chunks:
            print("❌ No chunks to index")
            return False

        print(f"\n🔧 Building FAISS index for {len(self.chunks)} chunks...")
        start_time = time.time()
        
        # Extract texts
        texts = [c["text"] for c in self.chunks]
        
        # Generate embeddings in batches
        print("📊 Generating embeddings...")
        embeddings_list = []
        
        for i in tqdm(range(0, len(texts), AIPodConfig.BATCH_SIZE), 
                     desc="Embedding", 
                     unit="batch"):
            batch_texts = texts[i:i + AIPodConfig.BATCH_SIZE]
            batch_embeddings = self.embedder.encode(
                batch_texts, 
                show_progress_bar=False,
                convert_to_numpy=True
            )
            embeddings_list.append(batch_embeddings)
        
        # Combine embeddings
        all_embeddings = np.vstack(embeddings_list)
        
        print(f"📐 Embedding dimension: {all_embeddings.shape[1]}")
        print(f"📈 Total vectors: {all_embeddings.shape[0]}")
        
        # Create and save FAISS index
        print("🛠️ Creating FAISS index...")
        index = faiss.IndexFlatL2(all_embeddings.shape[1])
        index.add(all_embeddings.astype("float32"))
        
        faiss.write_index(index, AIPodConfig.FAISS_INDEX_PATH)
        
        # Save chunks
        with open(AIPodConfig.CHUNKS_PATH, "wb") as f:
            pickle.dump(self.chunks, f)
        
        # Create metadata summary
        metadata_summary = {
            "total_chunks": len(self.chunks),
            "languages": list(set(c["metadata"]["language"] for c in self.chunks if "language" in c["metadata"])),
            "documents": list(set(c["metadata"]["file_name"] for c in self.chunks if "file_name" in c["metadata"])),
            "built_at": datetime.datetime.now().isoformat(),
            "version": AIPodConfig.VERSION,
            "embedding_model": AIPodConfig.EMBEDDING_MODEL,
            "chunk_size": AIPodConfig.CHUNK_SIZE
        }
        
        with open(AIPodConfig.METADATA_PATH, "wb") as f:
            pickle.dump(metadata_summary, f)
        
        # Calibrate thresholds using the embeddings we already have
        print("\n🔧 Calibrating semantic thresholds...")
        thresholds = self.calibrate_thresholds(all_embeddings)
        
        # Save thresholds
        with open(AIPodConfig.THRESHOLDS_PATH, "wb") as f:
            pickle.dump(thresholds, f)
        
        elapsed = time.time() - start_time
        print(f"\n✅ Index built in {elapsed:.1f} seconds")
        print(f"✅ Thresholds calibrated and saved")
        
        return True
    
    # -----------------------------------------------------
    def calibrate_thresholds(self, embeddings: np.ndarray):
        """Calibrate semantic thresholds based on actual data"""
        print("   Analyzing similarity distribution...")
        
        if len(self.chunks) < 10 or embeddings.shape[0] < 10:
            # Not enough data, use defaults
            print("   ⚠️ Not enough data for calibration, using defaults")
            return {
                'high': 0.45,
                'medium': 0.30,
                'low': 0.20
            }
        
        # Sample chunks for calibration
        sample_size = min(50, len(self.chunks))
        sample_indices = random.sample(range(len(self.chunks)), sample_size)
        
        # Get embeddings for samples
        sample_embeddings = embeddings[sample_indices]
        
        # Calculate self-similarities (comparing each chunk to others)
        self_similarities = []
        
        # Create a temporary index for the samples
        temp_index = faiss.IndexFlatL2(embeddings.shape[1])
        temp_index.add(sample_embeddings.astype("float32"))
        
        for i, emb in enumerate(sample_embeddings):
            emb = emb.reshape(1, -1).astype("float32")
            
            # Search for 2 nearest neighbors (first is itself)
            distances, indices = temp_index.search(emb, 2)
            
            if indices.shape[1] >= 2:
                # Get similarity to the second nearest (most similar different chunk)
                similarity = 1 / (1 + distances[0][1])
                self_similarities.append(similarity)
        
        # Calculate cross-document similarities (random pairs)
        cross_similarities = []
        
        for _ in range(min(100, sample_size * 2)):
            i = random.randint(0, sample_size - 1)
            j = random.randint(0, sample_size - 1)
            
            if i != j:
                emb1 = sample_embeddings[i].reshape(1, -1).astype("float32")
                
                distances, _ = temp_index.search(emb1, 1)
                similarity = 1 / (1 + distances[0][0])
                cross_similarities.append(similarity)
        
        # Calculate statistics
        if self_similarities:
            avg_self = sum(self_similarities) / len(self_similarities)
            min_self = min(self_similarities)
            print(f"   • Similar (same topic): avg={avg_self:.2%}, min={min_self:.2%}")
        else:
            avg_self = 0.5
            min_self = 0.4
            print("   • Similar (same topic): using defaults")
        
        if cross_similarities:
            avg_cross = sum(cross_similarities) / len(cross_similarities)
            max_cross = max(cross_similarities)
            print(f"   • Random (different): avg={avg_cross:.2%}, max={max_cross:.2%}")
        else:
            avg_cross = 0.2
            max_cross = 0.3
            print("   • Random (different): using defaults")
        
        # Set thresholds based on data
        thresholds = {
            'high': max(min_self * 0.8, avg_self * 0.6),  # 80% of min self-similarity
            'medium': max(avg_cross * 1.5, min_self * 0.5),  # Above average cross
            'low': avg_cross * 1.2  # Slightly above average cross
        }
        
        # Ensure reasonable bounds
        thresholds['high'] = max(0.40, min(0.65, thresholds['high']))
        thresholds['medium'] = max(0.28, min(0.45, thresholds['medium']))
        thresholds['low'] = max(0.18, min(0.30, thresholds['low']))
        
        print(f"\n📊 Calibrated Thresholds:")
        print(f"   • High relevance: > {thresholds['high']:.1%}")
        print(f"   • Medium relevance: {thresholds['medium']:.1%} - {thresholds['high']:.1%}")
        print(f"   • Low relevance: {thresholds['low']:.1%} - {thresholds['medium']:.1%}")
        print(f"   • Off-topic: < {thresholds['low']:.1%}")
        
        return thresholds


# Main
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI POD - Semantic Document Ingestion")
    print("=" * 60)
    print(f"Company: {AIPodConfig.COMPANY_NAME}")
    print(f"Version: {AIPodConfig.VERSION}")
    print(f"Embedding: {AIPodConfig.EMBEDDING_MODEL}")
    print("=" * 60)

    total_start = time.time()
    
    try:
        # Initialize processor
        processor = DocumentProcessor()
        
        # Process all files
        if processor.process_all_files():
            # Build index and calibrate thresholds
            if processor.build_index():
                total_elapsed = time.time() - total_start
                
                print("\n" + "=" * 60)
                print("🎉 INGESTION COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"📊 Final Statistics:")
                print(f"   • Files processed: {processor.total_files}")
                print(f"   • Total chunks: {len(processor.chunks)}")
                print(f"   • Total time: {total_elapsed:.1f} seconds")
                print(f"   • Index saved to: {AIPodConfig.INDEX_DIR}")
                print("\n➡ Next step: python query_system.py")
                print("=" * 60)
            else:
                print("\n❌ Failed to build index")
        else:
            print("\n❌ Failed to process files")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Ingestion interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()