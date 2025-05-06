# matcher/vector_store.py
import faiss, pickle, numpy as np
from config import settings

def build_faiss_index(embeddings, ids):
    d = settings.VECTOR_DIM
    idx = faiss.IndexFlatIP(d)
    mat = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(mat)
    idx.add(mat)
    with open(settings.VECTOR_INDEX_PATH, "wb") as f:
        pickle.dump((idx, ids), f)

def load_index():
    with open(settings.VECTOR_INDEX_PATH, "rb") as f:
        return pickle.load(f)

def search(query_emb, top_k=10):
    idx, ids = load_index()
    q = np.array([query_emb], dtype="float32")
    faiss.normalize_L2(q)
    D, I = idx.search(q, top_k)
    return [(ids[i], float(D[0][j])) for j,i in enumerate(I[0])]
