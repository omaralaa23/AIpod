"""
AI POD Configuration - Single Source of Truth
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIPodConfig:
    """Configuration for AI POD system - Single source of truth"""
    
    # GROQ CONFIGURATION 
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Groq Models
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # For embeddings
    LLM_MODEL_FAST = "llama-3.1-8b-instant"  # Default for day-to-day
    LLM_MODEL_ADVANCED = "llama-3.3-70b-versatile"  # For complex reasoning
    
    # PROJECT METADATA
    COMPANY_NAME = "GIG EGYPT LIFE TAKAFUL"
    PROJECT_NAME = "AI POD"
    VERSION = "1.3.0"
    DEPARTMENT = "Multi-Department"  #supports any department
    
    # FILE PATHS
    # Use relative paths - works on any machine
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOCUMENTS_DIR = os.path.join(BASE_DIR, "HRandIT_documents")
    INDEX_DIR = os.path.join(BASE_DIR, "indices")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    
    # FAISS INDEX PATHS
    FAISS_INDEX_PATH = os.path.join(INDEX_DIR, "faiss.index")
    METADATA_PATH = os.path.join(INDEX_DIR, "metadata.pkl")
    CHUNKS_PATH = os.path.join(INDEX_DIR, "chunks.pkl")
    THRESHOLDS_PATH = os.path.join(INDEX_DIR, "thresholds.pkl")
    
    # EMBEDDING CONFIG 
    CHUNK_SIZE = 1000  # Characters per chunk
    CHUNK_OVERLAP = 200  # Overlap between chunks
    BATCH_SIZE = 32  # For embedding generation
    
    #SEARCH CONFIG
    DEFAULT_SEARCH_K = 15  # Number of candidates to retrieve
    TOP_K_RESULTS = 3  # Number of results to return
    
    #  SEMANTIC THRESHOLDS (Auto-calibrated)
    # These will be overridden by calibration
    HIGH_THRESHOLD = 0.45
    MEDIUM_THRESHOLD = 0.30
    LOW_THRESHOLD = 0.20
    
    # SECURITY CONFIG
    ALLOWED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    #TOKEN LIMITS
    MAX_TOKENS_PER_QUERY = 4000
    MAX_CHUNKS_PER_QUERY = 5
    
    # CREATE DIRECTORIES
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        os.makedirs(cls.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(cls.INDEX_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        return True

# Create directories on import
AIPodConfig.create_directories()