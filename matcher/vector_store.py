# matcher/vector_store.py
import faiss, numpy as np
import logging
import os
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

def build_faiss_index(embeddings, ids):
    """Build and save a FAISS index from embeddings."""
    try:
        logger.info("Converting embeddings to numpy array")
        
        # Process embeddings to ensure all are the same length
        processed_embeddings = []
        processed_ids = []
        expected_dim = 1536  # OpenAI's standard dimension
        
        for i, emb in zip(ids, embeddings):
            # Check if embedding is a list or array with valid values
            if isinstance(emb, (list, np.ndarray)) and len(emb) > 0:
                # Convert to numpy array if it's a list
                emb_array = np.array(emb)
                
                # Check if it's the expected dimension
                if emb_array.shape[0] == expected_dim:
                    processed_embeddings.append(emb_array)
                    processed_ids.append(i)
                else:
                    logger.warning(f"Skipping embedding with incorrect dimension: {emb_array.shape[0]} (expected {expected_dim})")
            else:
                logger.warning(f"Skipping invalid embedding type: {type(emb)}")
        
        if not processed_embeddings:
            logger.error("No valid embeddings found for indexing")
            raise ValueError("No valid embeddings found")
            
        # Convert to a single numpy array
        mat = np.array(processed_embeddings).astype('float32')
        logger.info(f"Embeddings array shape: {mat.shape}")
        
        # Initialize index with correct dimension
        d = mat.shape[1]  # Get dimension from first embedding
        logger.info(f"Creating FAISS index with dimension {d}")
        idx = faiss.IndexFlatL2(d)
        
        # Add vectors to index
        logger.info("Adding vectors to index")
        idx.add(mat)
        
        # Save index and IDs
        local_vector_path = "./data/vector_index"
        logger.info(f"Creating directory {os.path.dirname(local_vector_path)}")
        os.makedirs(os.path.dirname(local_vector_path), exist_ok=True)

        logger.info(f"Saving FAISS index to {local_vector_path}")
        faiss.write_index(idx, local_vector_path)

        logger.info(f"Saving IDs to {local_vector_path}.ids.npy")
        np.save(local_vector_path + ".ids.npy", np.array(processed_ids))
        logger.info("Index and IDs saved successfully")
        
        return idx, processed_ids
    except Exception as e:
        logger.error(f"Error building FAISS index: {str(e)}")
        raise

def load_index():
    """Load FAISS index and IDs, or build them if they don't exist."""
    # Use local path instead of settings
    local_vector_path = "./data/vector_index"
    logger.warning(f"Using local vector path: {local_vector_path} instead of {settings.VECTOR_INDEX_PATH}")
    index_path = os.path.expanduser(local_vector_path)
    ids_path = index_path + ".ids.npy"
    
    # Check if index files exist
    if os.path.exists(index_path) and os.path.exists(ids_path):
        try:
            logger.info(f"Loading FAISS index from {index_path}")
            idx = faiss.read_index(index_path)
            logger.info(f"Loading IDs from {ids_path}")
            ids = np.load(ids_path).tolist()
            logger.info(f"Loaded index with {idx.ntotal} vectors and {len(ids)} IDs")
            return idx, ids
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            logger.error("Will try to rebuild index")
            # Fall through to rebuild index
    
    # If we get here, either the files don't exist or there was an error loading them
    logger.info("Index files not found or error loading. Building new index from opportunities...")
    
    # Import here to avoid circular imports
    import json
    from config import settings
    
    # Load opportunities
    try:
        with open("data/opportunities.jsonl") as f:
            opps = [json.loads(line) for line in f]
            
        logger.info(f"Loaded {len(opps)} opportunities for indexing")
        
        # Extract embeddings
        embeddings = []
        ids = []
        for i, opp in enumerate(opps):
            if "embedding" in opp:
                embeddings.append(opp["embedding"])
                ids.append(i)
                
        if not embeddings:
            logger.error("No embeddings found in opportunities. Cannot build index.")
            raise ValueError("No embeddings found in opportunities")
            
        logger.info(f"Found {len(embeddings)} embeddings for indexing")
        
        # Build and save index
        build_faiss_index(embeddings, ids)
        
        # Load the newly created index
        idx = faiss.read_index(index_path)
        ids = np.load(ids_path).tolist()
        
        logger.info(f"Built and loaded new index with {idx.ntotal} vectors and {len(ids)} IDs")
        return idx, ids
        
    except Exception as e:
        logger.error(f"Failed to build index: {str(e)}")
        # Create empty index for now
        d = 1536  # OpenAI's embedding dimension
        idx = faiss.IndexFlatL2(d)
        return idx, []

def search(query_emb, top_k=10, filter_fn=None):
    """
    Search for similar items using FAISS.
    Args:
        query_emb: Query embedding vector
        top_k: Number of results to return
        filter_fn: Optional function to filter results before returning
    """
    try:
        logger.info(f"Starting FAISS search with filter_fn={filter_fn is not None}")
        
        # Ensure query embedding is valid
        if not isinstance(query_emb, (list, np.ndarray)) or len(query_emb) == 0:
            logger.error(f"Invalid query embedding: {type(query_emb)}")
            return []
            
        # Load or build the index
        try:
            idx, ids = load_index()
            if not ids:
                logger.warning("Index has no IDs, returning empty results")
                return []
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            return []
            
        # Convert query to numpy array
        q = np.array([query_emb], dtype="float32")
        
        # Ensure the dimensions match
        if q.shape[1] != idx.d:
            logger.error(f"Query embedding dimension {q.shape[1]} does not match index dimension {idx.d}")
            return []
            
        # Check if there are enough items in the index
        actual_k = min(top_k * 20, idx.ntotal)  # Cannot search for more items than in the index
        if actual_k == 0:
            logger.warning("Index is empty, no search results")
            return []
            
        # Get many more results than needed to account for filtering
        logger.info(f"Searching for {actual_k} results")
        D, I = idx.search(q, actual_k)
        
        results = []
        filtered_count = 0
        total_checked = 0
        
        # Keep searching until we have enough results or run out of candidates
        if len(I) > 0 and len(I[0]) > 0:
            for j, i in enumerate(I[0]):
                # Check if the index is valid (should be within range of ids)
                if i < 0 or i >= len(ids):
                    logger.warning(f"Invalid index {i}, skipping")
                    continue
                    
                total_checked += 1
                if filter_fn:
                    try:
                        should_include = filter_fn(ids[i])
                        logger.info(f"Filtering result {ids[i]}: {should_include}")
                        if not should_include:
                            filtered_count += 1
                            continue
                    except Exception as e:
                        logger.error(f"Error in filter function: {str(e)}")
                        filtered_count += 1
                        continue
                
                results.append((ids[i], float(D[0][j])))
                if len(results) >= top_k:
                    break
        
        logger.info(f"Checked {total_checked} results, filtered out {filtered_count}, returning {len(results)} results")
        
        # If we don't have enough results after filtering, log a warning
        if len(results) < top_k:
            logger.warning(f"Could only find {len(results)} results after filtering (requested {top_k})")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return []
