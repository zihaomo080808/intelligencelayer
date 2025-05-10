import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class RocchioUpdater:
    def __init__(self, alpha: float = 0.8, beta: float = 0.2, gamma: float = 0.1):
        """
        Initialize the Rocchio algorithm updater.
        
        Args:
            alpha: Weight for the original query vector
            beta: Weight for the relevant documents
            gamma: Weight for the non-relevant documents
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        
    def update_embedding(
        self,
        original_embedding: List[float],
        relevant_embeddings: List[List[float]],
        non_relevant_embeddings: List[List[float]]
    ) -> List[float]:
        """
        Update the user embedding using the Rocchio algorithm.
        
        Args:
            original_embedding: The current user embedding
            relevant_embeddings: List of embeddings from items the user liked
            non_relevant_embeddings: List of embeddings from items the user skipped
            
        Returns:
            Updated user embedding
        """
        try:
            # Convert to numpy arrays for efficient computation
            original = np.array(original_embedding)
            
            # Handle relevant documents
            if relevant_embeddings:
                relevant = np.array(relevant_embeddings)
                relevant_centroid = np.mean(relevant, axis=0)
            else:
                relevant_centroid = np.zeros_like(original)
                
            # Handle non-relevant documents
            if non_relevant_embeddings:
                non_relevant = np.array(non_relevant_embeddings)
                non_relevant_centroid = np.mean(non_relevant, axis=0)
            else:
                non_relevant_centroid = np.zeros_like(original)
            
            # Apply Rocchio formula
            new_embedding = (
                self.alpha * original +
                self.beta * relevant_centroid -
                self.gamma * non_relevant_centroid
            )
            
            # Normalize the embedding
            norm = np.linalg.norm(new_embedding)
            if norm > 0:
                new_embedding = new_embedding / norm
                
            return new_embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error updating embedding with Rocchio: {str(e)}")
            return original_embedding  # Return original embedding if update fails