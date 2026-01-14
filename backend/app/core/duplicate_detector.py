"""
Duplicate detection system using semantic similarity and content hashing.

Detects duplicate assignments even with minor variations in case, punctuation, or phrasing.
"""

import hashlib
import logging
import re
from typing import List, Optional, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate assignments using multiple strategies:
    1. Exact match via content hash
    2. Fuzzy match via normalized text
    3. Semantic similarity via embeddings (optional, requires sentence-transformers)
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = False
        
        # Try to import sentence-transformers for semantic similarity
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, lightweight model
            self.use_embeddings = True
            logger.info("Semantic similarity enabled with sentence-transformers")
        except ImportError:
            logger.warning(
                "sentence-transformers not available. "
                "Duplicate detection will use hash and fuzzy matching only. "
                "Install with: pip install sentence-transformers"
            )
            self.model = None
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison by:
        - Converting to lowercase
        - Removing extra whitespace
        - Removing punctuation
        - Removing common stop words (optional)
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove punctuation but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def calculate_content_hash(self, title: str, description: str) -> str:
        """
        Calculate MD5 hash of normalized content.
        Used for exact duplicate detection.
        """
        # Normalize both title and description
        normalized = self.normalize_text(f"{title} {description}")
        
        # Calculate hash
        content_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()
        
        return content_hash
    
    def calculate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Calculate semantic embedding vector for text.
        Returns None if sentence-transformers not available.
        """
        if not self.use_embeddings or not self.model:
            return None
        
        try:
            # Encode text to vector
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error calculating embedding: {e}")
            return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        try:
            import numpy as np
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def fuzzy_match_ratio(self, text1: str, text2: str) -> float:
        """
        Calculate fuzzy matching ratio between two texts.
        Uses Levenshtein distance ratio.
        """
        try:
            from difflib import SequenceMatcher
            
            # Normalize texts
            norm1 = self.normalize_text(text1)
            norm2 = self.normalize_text(text2)
            
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, norm1, norm2).ratio()
            return ratio
        except Exception as e:
            logger.error(f"Error calculating fuzzy match: {e}")
            return 0.0
    
    async def check_duplicate(
        self,
        title: str,
        description: str,
        existing_assignments: List[Dict]
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if assignment is a duplicate of existing assignments.
        
        Args:
            title: Assignment title
            description: Assignment description
            existing_assignments: List of existing assignments with content_hash and optionally embeddings
        
        Returns:
            Tuple of (is_duplicate, duplicate_id, similarity_score)
        """
        if not existing_assignments:
            return False, None, 0.0
        
        # Calculate hash for new assignment
        new_hash = self.calculate_content_hash(title, description)
        
        # Step 1: Check for exact hash match (fastest)
        for assignment in existing_assignments:
            if assignment.get('content_hash') == new_hash:
                logger.info(f"Exact duplicate found (hash match): {assignment.get('_id')}")
                return True, str(assignment.get('_id')), 1.0
        
        # Step 2: Fuzzy text matching
        new_text = f"{title} {description}"
        best_fuzzy_match = 0.0
        best_fuzzy_id = None
        
        for assignment in existing_assignments:
            existing_text = f"{assignment.get('title', '')} {assignment.get('description', '')}"
            fuzzy_score = self.fuzzy_match_ratio(new_text, existing_text)
            
            if fuzzy_score > best_fuzzy_match:
                best_fuzzy_match = fuzzy_score
                best_fuzzy_id = str(assignment.get('_id'))
            
            # If fuzzy match is very high, consider it a duplicate
            if fuzzy_score >= self.similarity_threshold:
                logger.info(f"Fuzzy duplicate found (score: {fuzzy_score:.2f}): {assignment.get('_id')}")
                return True, str(assignment.get('_id')), fuzzy_score
        
        # Step 3: Semantic similarity (if available)
        if self.use_embeddings:
            new_embedding = self.calculate_embedding(new_text)
            
            if new_embedding:
                best_semantic_match = 0.0
                best_semantic_id = None
                
                for assignment in existing_assignments:
                    existing_embedding = assignment.get('content_embedding')
                    
                    if existing_embedding:
                        semantic_score = self.cosine_similarity(new_embedding, existing_embedding)
                        
                        if semantic_score > best_semantic_match:
                            best_semantic_match = semantic_score
                            best_semantic_id = str(assignment.get('_id'))
                        
                        # If semantic similarity is high, consider it a duplicate
                        if semantic_score >= self.similarity_threshold:
                            logger.info(f"Semantic duplicate found (score: {semantic_score:.2f}): {assignment.get('_id')}")
                            return True, str(assignment.get('_id')), semantic_score
                
                # Return best match if above threshold
                if best_semantic_match >= self.similarity_threshold:
                    return True, best_semantic_id, best_semantic_match
        
        # Use best fuzzy match as the similarity score
        logger.info(f"No duplicate found. Best match score: {best_fuzzy_match:.2f}")
        return False, best_fuzzy_id if best_fuzzy_match > 0.5 else None, best_fuzzy_match
    
    def prepare_assignment_data(self, title: str, description: str) -> Dict:
        """
        Prepare assignment data with hash and embedding for storage.
        
        Returns:
            Dict with content_hash and optionally content_embedding
        """
        data = {
            'content_hash': self.calculate_content_hash(title, description)
        }
        
        # Add embedding if available
        if self.use_embeddings:
            text = f"{title} {description}"
            embedding = self.calculate_embedding(text)
            if embedding:
                data['content_embedding'] = embedding
        
        return data


# Global duplicate detector instance
_duplicate_detector = None

def get_duplicate_detector(similarity_threshold: float = 0.85) -> DuplicateDetector:
    """Get or create global duplicate detector instance"""
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector(similarity_threshold)
    return _duplicate_detector
