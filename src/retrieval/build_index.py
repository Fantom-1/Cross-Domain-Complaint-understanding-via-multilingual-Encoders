"""Build a retrieval gallery from a single approved corpus split."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.evaluate_retrieval import _encode_xlmv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-dir", required=True, help="Contrastive run directory")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--include-text", action="store_true",
                        help="Store complaint narratives in metadata; protect the resulting index")
    args = parser.parse_args()

    gallery = pd.read_csv(args.gallery_csv, keep_default_na=False)
    required = {"example_id", "text", "label", "domain"}
    missing = required - set(gallery.columns)
    if missing:
        raise ValueError(f"Gallery CSV missing columns: {sorted(missing)}")
    if gallery["example_id"].duplicated().any():
        raise ValueError("Gallery contains duplicate example IDs")
    if gallery["text"].astype(str).str.strip().eq("").any():
        raise ValueError("Gallery contains empty complaint text")

    output = Path(args.output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing index directory: {output}")
    output.mkdir(parents=True)

    model_dir = Path(args.model_dir).resolve()
    config = json.loads((model_dir / "contrastive_config.json").read_text(encoding="utf-8"))
    vectors = _encode_xlmv(
        gallery["text"].astype(str).tolist(),
        str(config["model_name"]),
        str(config["revision"]),
        str(model_dir),
        args.max_length,
        args.batch_size,
    )
    np.save(output / "gallery_embeddings.npy", vectors.astype(np.float32), allow_pickle=False)
    columns = ["example_id", "label", "domain"]
    if args.include_text:
        columns.append("text")
    gallery[columns].to_csv(output / "gallery_metadata.csv", index=False)
    manifest = {
        "gallery_csv": str(Path(args.gallery_csv).resolve()),
        "gallery_sha256": hashlib.sha256(Path(args.gallery_csv).read_bytes()).hexdigest(),
        "embedding_sha256": hashlib.sha256((output / "gallery_embeddings.npy").read_bytes()).hexdigest(),
        "rows": len(gallery),
        "dimension": int(vectors.shape[1]),
        "model_dir": str(model_dir),
        "max_length": args.max_length,
        "contains_complaint_text": bool(args.include_text),
        "relevance_warning": "This index contains embeddings only; weak labels are not semantic relevance judgements.",
    }
    (output / "index_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
