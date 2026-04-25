"""Management command to populate ChromaDB with SBERT food name/alias embeddings."""

from django.core.management.base import BaseCommand
from django.conf import settings

BATCH_SIZE = 256


class Command(BaseCommand):
    help = (
        "Populate (or refresh) the ChromaDB vector store with SBERT embeddings for all "
        "Food names and FoodAlias records. Safe to re-run: uses upsert."
    )

    def handle(self, *args, **options):
        from sentence_transformers import SentenceTransformer
        import chromadb
        from tqdm import tqdm
        from meals.models import Food, FoodAlias

        model_name = getattr(
            settings, "SBERT_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        db_path = str(getattr(settings, "CHROMA_DB_PATH", "chroma_db"))

        self.stdout.write(f"Loading SBERT model '{model_name}' …")
        model = SentenceTransformer(model_name)

        self.stdout.write(f"Connecting to ChromaDB at '{db_path}' …")
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(
            name="foods",
            metadata={"hnsw:space": "cosine"},
        )

        # ── Food names ────────────────────────────────────────────────────────
        foods = list(Food.objects.values("bls_code", "name"))
        self.stdout.write(f"Embedding {len(foods)} food names …")

        for start in tqdm(range(0, len(foods), BATCH_SIZE), desc="Food names"):
            batch = foods[start : start + BATCH_SIZE]
            texts = [f["name"] for f in batch]
            embeddings = model.encode(texts).tolist()
            collection.upsert(
                ids=[f"name::{f['bls_code']}" for f in batch],
                embeddings=embeddings,
                metadatas=[
                    {"bls_code": f["bls_code"], "type": "name", "alias": ""}
                    for f in batch
                ],
            )

        # ── FoodAlias entries ─────────────────────────────────────────────────
        aliases = list(
            FoodAlias.objects.select_related("food").values(
                "id", "alias", "food__bls_code"
            )
        )
        self.stdout.write(f"Embedding {len(aliases)} food aliases …")

        for start in tqdm(range(0, len(aliases), BATCH_SIZE), desc="Aliases"):
            batch = aliases[start : start + BATCH_SIZE]
            texts = [a["alias"] for a in batch]
            embeddings = model.encode(texts).tolist()
            collection.upsert(
                ids=[f"alias::{a['id']}" for a in batch],
                embeddings=embeddings,
                metadatas=[
                    {
                        "bls_code": a["food__bls_code"],
                        "type": "alias",
                        "alias": a["alias"],
                    }
                    for a in batch
                ],
            )

        total = collection.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. ChromaDB collection 'foods' now has {total} documents."
            )
        )
