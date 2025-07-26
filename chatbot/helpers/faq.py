import json
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def load_faq_embeddings(path):
    with open(path, "r") as f:
        return json.load(f)

def match_faq(user_query, faqs, embed_func, threshold=0.85):
    query_vector = embed_func(user_query)
    scores = [cosine_similarity([query_vector], [f["embedding"]])[0][0] for f in faqs]
    best = int(np.argmax(scores))
    if scores[best] >= threshold:
        return faqs[best]["answer"]
    return None
