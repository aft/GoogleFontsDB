"""
Build font embeddings for semantic search.

Requires:
    pip install openai umap-learn numpy

Set OPENAI_API_KEY environment variable before running.

Usage:
    python build_embeddings.py
"""

import json
import os
import sys
import numpy as np
from openai import OpenAI

MODEL = "text-embedding-3-large"
DIMS = 1024
MOOD_WEIGHT = 0.6
KEYWORDS_WEIGHT = 0.4
BATCH_SIZE = 200  # OpenAI embedding batch limit is 2048

INPUT_FILE = "font-database-decorated.json"
OUTPUT_FILE = "font-embeddings.json"


def get_embeddings(client, texts, model=MODEL, dimensions=DIMS):
    """Get embeddings for a list of texts in batches."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(input=batch, model=model, dimensions=dimensions)
        all_embeddings.extend([d.embedding for d in resp.data])
        print(f"  Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return all_embeddings


def normalize(vec):
    """L2 normalize a vector."""
    arr = np.array(vec, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Load font data
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    fonts = db["fonts"]

    # Collect fonts that have mood or keywords
    font_names = []
    mood_texts = []
    keyword_texts = []

    for name, data in fonts.items():
        mood = data.get("mood", "")
        keywords = data.get("keywords", [])
        if not mood and not keywords:
            continue
        font_names.append(name)
        mood_texts.append(mood if mood else name)
        keyword_texts.append(", ".join(keywords) if keywords else name)

    print(f"Found {len(font_names)} fonts with mood/keywords data.")
    print(f"Skipping {len(fonts) - len(font_names)} fonts without data.\n")

    # Embed mood texts
    print("Embedding mood texts...")
    mood_vecs = get_embeddings(client, mood_texts)

    # Embed keyword texts
    print("\nEmbedding keyword texts...")
    keyword_vecs = get_embeddings(client, keyword_texts)

    # Combine with weighting
    print("\nCombining vectors (mood 0.6 + keywords 0.4)...")
    combined = {}
    for i, name in enumerate(font_names):
        mood_arr = np.array(mood_vecs[i], dtype=np.float64)
        kw_arr = np.array(keyword_vecs[i], dtype=np.float64)
        weighted = MOOD_WEIGHT * mood_arr + KEYWORDS_WEIGHT * kw_arr
        combined[name] = normalize(weighted)

    # Reduce to 2D with UMAP
    print("Running UMAP dimensionality reduction...")
    import umap

    names_list = list(combined.keys())
    vectors = np.array([combined[n] for n in names_list])

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        random_state=42
    )
    coords_2d = reducer.fit_transform(vectors)

    # Normalize 2D coords to 0-1 range
    mins = coords_2d.min(axis=0)
    maxs = coords_2d.max(axis=0)
    coords_2d = (coords_2d - mins) / (maxs - mins)

    # Build output (save all three vectors for different clustering modes)
    print("Building output...")
    output = {}
    for i, name in enumerate(names_list):
        mood_normalized = normalize(np.array(mood_vecs[i], dtype=np.float64))
        kw_normalized = normalize(np.array(keyword_vecs[i], dtype=np.float64))
        output[name] = {
            "vec": [round(float(x), 6) for x in combined[name]],
            "mood_vec": [round(float(x), 6) for x in mood_normalized],
            "kw_vec": [round(float(x), 6) for x in kw_normalized],
            "pos": [round(float(coords_2d[i][0]), 5), round(float(coords_2d[i][1]), 5)]
        }

    # Add metadata
    result = {
        "model": MODEL,
        "dimensions": DIMS,
        "mood_weight": MOOD_WEIGHT,
        "keywords_weight": KEYWORDS_WEIGHT,
        "total_fonts": len(output),
        "fonts": output
    }

    # Save
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nDone! {OUTPUT_FILE} ({file_size / 1024 / 1024:.1f} MB)")
    print(f"Embedded {len(output)} fonts.")


if __name__ == "__main__":
    main()
