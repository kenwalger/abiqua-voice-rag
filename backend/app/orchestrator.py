import asyncio
import os
import re
from dataclasses import dataclass
from typing import Any

from app.llama_mongodb_patch import apply_llama_mongodb_objectid_patch

apply_llama_mongodb_objectid_patch()

from anthropic import Anthropic
from bson import ObjectId
from bson.errors import InvalidId
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

from app.pipeline_log import log as plog
from app.pipeline_log import timed_async
from app.settings import get_settings

settings = get_settings()
os.environ.setdefault("MONGODB_URI", settings.MONGODB_URI)

SCORE_THRESHOLD = settings.SCORE_THRESHOLD
SERIAL_PATTERN = re.compile(r"^\s*(?:#|serial\s*)?(\d{4,9})\s*$", re.IGNORECASE)

SYSTEM_PROMPT = """
You are the voice of The Abiqua Collection, a digital museum
documenting the history and provenance of Smith and Wesson revolvers.

Your narrations are authoritative, historically grounded, and written
for an audience that appreciates precision. You speak like a knowledgeable
collector and historian, not a salesperson.

Rules:
- Write in present tense where appropriate for historical description.
- Never speculate beyond what the source records support.
- If image references are present, close with exactly this sentence,
  substituting N: 'There are N images available to view.'
- If no images are present, omit the image sentence entirely.
- Target length: 3 to 5 sentences. Never exceed 8 sentences.
- Do not use bullet points, headers, or markdown formatting.
- Do not begin with 'I' or 'The Abiqua Collection'.
""".strip()


@dataclass
class OrchestratorResult:
    narration_text: str
    image_count: int
    image_refs: list[dict[str, Any]]
    source_meta: dict[str, Any]
    confidence: float
    query_type: str
    collections_hit: list[str]


mongo_client = MongoClient(settings.MONGODB_URI)
db = mongo_client[settings.MONGODB_DB_NAME]

embed_model = OpenAIEmbedding(
    model=settings.LLAMAINDEX_EMBED_MODEL,
    api_key=settings.OPENAI_API_KEY,
)
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def build_index(collection_name: str, vector_index_name: str) -> VectorStoreIndex:
    vector_store = MongoDBAtlasVectorSearch(
        mongodb_client=mongo_client,
        db_name=settings.MONGODB_DB_NAME,
        collection_name=collection_name,
        vector_index_name=vector_index_name,
        embedding_key=settings.MONGODB_EMBEDDING_FIELD,
        text_key="text",
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=embed_model,
    )


index_firearms = build_index(
    settings.MONGODB_COLLECTION_FIREARMS_CHUNKS,
    settings.MONGODB_INDEX_FIREARMS_CHUNKS,
)
index_historical = build_index(
    settings.MONGODB_COLLECTION_HISTORICAL_CHUNKS,
    settings.MONGODB_INDEX_HISTORICAL_CHUNKS,
)
index_manufacturers = build_index(
    settings.MONGODB_COLLECTION_MANUFACTURERS_CHUNKS,
    settings.MONGODB_INDEX_MANUFACTURERS_CHUNKS,
)


def classify_query(query: str) -> str:
    if SERIAL_PATTERN.match(query):
        return "serial_number"
    return "natural_language"


def extract_serial_number(query: str) -> str | None:
    match = SERIAL_PATTERN.match(query)
    if not match:
        return None
    return match.group(1)


async def embed_query(query: str) -> list[float]:
    return await asyncio.to_thread(embed_model.get_query_embedding, query)


def _retrieve_with_index(index: VectorStoreIndex, query: str, top_k: int) -> list[NodeWithScore]:
    retriever = index.as_retriever(similarity_top_k=top_k)
    return retriever.retrieve(query)


def _is_firearms_chunk(chunk: NodeWithScore) -> bool:
    metadata = chunk.node.metadata or {}
    source = str(metadata.get("chunk_source_collection", "")).lower()
    return source.startswith("firearms")


def _direct_vector_search_firearms(
    query_vector: list[float], top_k: int, source_firearm_id: Any | None = None
) -> list[NodeWithScore]:
    search_stage: dict[str, Any] = {
        "index": settings.MONGODB_INDEX_FIREARMS_CHUNKS,
        "path": settings.MONGODB_EMBEDDING_FIELD,
        "queryVector": query_vector,
        "numCandidates": max(top_k * 10, 50),
        "limit": top_k,
    }
    pipeline = [
        {"$vectorSearch": search_stage},
        {
            "$project": {
                "text": 1,
                "source_firearm_id": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    rows = list(db[settings.MONGODB_COLLECTION_FIREARMS_CHUNKS].aggregate(pipeline))
    if source_firearm_id is not None:
        expected = str(source_firearm_id)
        rows = [row for row in rows if str(row.get("source_firearm_id")) == expected]
    out: list[NodeWithScore] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        if "source_firearm_id" not in metadata and row.get("source_firearm_id"):
            metadata["source_firearm_id"] = str(row["source_firearm_id"])
        node = TextNode(text=row.get("text", ""), metadata=metadata)
        out.append(NodeWithScore(node=node, score=float(row.get("score") or 0.0)))
    return out


async def retrieve(
    query: str,
    query_type: str,
    top_k: int,
    query_embedding: list[float],
    serial_parent_id: Any | None = None,
) -> list[NodeWithScore]:
    plog(
        "retrieve start query_type=%s top_k=%s serial_parent_id=%s q_preview=%s",
        query_type,
        top_k,
        serial_parent_id,
        (query[:120] + "…") if len(query) > 120 else query,
    )
    if query_type == "serial_number":
        if serial_parent_id is not None:
            nodes = await asyncio.to_thread(
                _direct_vector_search_firearms,
                query_embedding,
                top_k,
                serial_parent_id,
            )
        else:
            nodes = await asyncio.to_thread(_retrieve_with_index, index_firearms, query, top_k)
        if not nodes and serial_parent_id is None:
            nodes = await asyncio.to_thread(_direct_vector_search_firearms, query_embedding, top_k)
        filtered = [n for n in nodes if (n.score or 0.0) >= SCORE_THRESHOLD]
        filtered.sort(key=lambda n: n.score or 0.0, reverse=True)
        # Serial queries can be exact identifiers where semantic scores are lower;
        # if thresholding removes all candidates, fall back to raw top-k.
        if filtered:
            out = filtered[:top_k]
            plog("retrieve serial path=%s chunks=%s", "filtered", len(out))
            return out
        nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
        out = nodes[:top_k]
        plog("retrieve serial path=%s chunks=%s", "raw_topk_fallback", len(out))
        return out

    results = await asyncio.gather(
        asyncio.to_thread(_retrieve_with_index, index_firearms, query, top_k),
        asyncio.to_thread(_retrieve_with_index, index_historical, query, top_k),
        asyncio.to_thread(_retrieve_with_index, index_manufacturers, query, top_k),
    )
    merged = [node for sublist in results for node in sublist]
    merged.sort(key=lambda n: n.score or 0.0, reverse=True)
    filtered_nl = [n for n in merged if (n.score or 0.0) >= SCORE_THRESHOLD][:top_k]
    plog(
        "retrieve natural_language merged=%s after_threshold=%s",
        len(merged),
        len(filtered_nl),
    )
    return filtered_nl


def fetch_parent_firearms(source_ids: list[str]) -> dict[str, dict[str, Any]]:
    object_ids: list[ObjectId] = []
    for source_id in source_ids:
        if not source_id:
            continue
        try:
            object_ids.append(ObjectId(source_id))
        except InvalidId:
            continue
    if not object_ids:
        return {}

    docs = db[settings.MONGODB_COLLECTION_FIREARMS].find(
        {"_id": {"$in": object_ids}},
        {
            "images": 1,
            "factory_letter": 1,
            "serial_number": 1,
            "year": 1,
            "estimated_year": 1,
            "finish": 1,
            "model": 1,
            "series": 1,
            "caliber": 1,
            "short_url": 1,
        },
    )
    return {str(doc["_id"]): doc for doc in docs}


def find_parent_firearm_by_serial(serial_number: str) -> dict[str, Any] | None:
    projection = {
        "qr_code_base64": 0,
        settings.MONGODB_EMBEDDING_FIELD: 0,
        "embedding_updated_at": 0,
        "sku": 0,
        "short_code": 0,
        "display_card_printed": 0,
        "sku_card_printed": 0,
        "box_sticker_printed": 0,
        "appraised_value": 0,
        "price_paid": 0,
        "created_at": 0,
        "updated_at": 0,
    }
    doc = db[settings.MONGODB_COLLECTION_FIREARMS].find_one(
        {"serial_number": serial_number},
        projection,
    )
    if doc is not None:
        return doc

    if serial_number.isdigit():
        return db[settings.MONGODB_COLLECTION_FIREARMS].find_one(
            {"serial_number": int(serial_number)},
            projection,
        )
    return None


def build_image_refs(parent_docs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for doc_id, doc in parent_docs.items():
        images = doc.get("images") or []
        for idx, image in enumerate(images):
            if isinstance(image, dict):
                filename = image.get("filename") or image.get("url") or image.get("path")
                caption_raw = image.get("caption")
            else:
                filename = str(image)
                caption_raw = None

            if caption_raw is None or isinstance(caption_raw, str):
                caption = caption_raw
            else:
                caption = str(caption_raw)

            if not filename:
                continue

            if filename.startswith("http://") or filename.startswith("https://"):
                url = filename
            elif settings.IMAGE_BASE_URL:
                url = f"{settings.IMAGE_BASE_URL.rstrip('/')}/{str(filename).lstrip('/')}"
            else:
                url = str(filename)

            refs.append(
                {
                    "image_id": doc_id,
                    "url": url,
                    "caption": caption,
                    "primary": idx == 0,
                }
            )
    return refs


def _coerce_year_field(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def build_source_meta(chunks: list[NodeWithScore], parent_docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    top_chunk = chunks[0] if chunks else None
    top_score = float(top_chunk.score or 0.0) if top_chunk else 0.0

    top_parent = None
    if top_chunk:
        source_id = top_chunk.node.metadata.get("source_firearm_id")
        if source_id:
            top_parent = parent_docs.get(str(source_id))

    if top_parent:
        year_value = top_parent.get("year") or top_parent.get("estimated_year")
        conf = round(top_score, 4)
        short_url = str(top_parent.get("short_url")).strip() if top_parent.get("short_url") else None
        return {
            "model": str(top_parent.get("model") or "Unknown"),
            "serial_range": str(top_parent.get("serial_number") or "Unknown"),
            "year_start": _coerce_year_field(year_value),
            "year_end": None,
            "record_count": int(len(parent_docs)),
            "confidence": conf,
            "short_url": short_url,
            "record_url": short_url,
        }

    top_model = (
        top_chunk.node.metadata.get("model")
        if top_chunk and isinstance(top_chunk.node.metadata, dict)
        else None
    )
    conf = round(top_score, 4)
    return {
        "model": str(top_model or "Unknown"),
        "serial_range": "Unknown",
        "year_start": None,
        "year_end": None,
        "record_count": int(len(chunks)),
        "confidence": conf,
        "short_url": None,
        "record_url": None,
    }


def build_user_prompt(
    query: str,
    chunks: list[NodeWithScore],
    parent_docs: dict[str, dict[str, Any]],
    image_count: int,
) -> str:
    context_blocks: list[str] = []
    for chunk in chunks:
        source = chunk.node.metadata.get("chunk_source_collection", "unknown")
        source_id = chunk.node.metadata.get("source_firearm_id")
        parent = parent_docs.get(str(source_id), {}) if source_id else {}
        block = f"[Source: {source}]\n{chunk.node.text}"
        if parent.get("factory_letter"):
            block += "\n(Factory letter on file.)"
        if parent.get("short_url"):
            block += f"\nCollection URL: {parent['short_url']}"
        context_blocks.append(block)
    context = "\n\n".join(context_blocks)
    image_instruction = (
        f"Close with: There are {image_count} images available to view."
        if image_count > 0
        else "No images are available for this record."
    )
    return f"Query: {query}\n\nSource records:\n{context}\n\n{image_instruction}"


async def synthesize_narration(user_prompt: str) -> str:
    response = await asyncio.to_thread(
        anthropic_client.messages.create,
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return "\n".join(text_parts).strip()


def _chunk_collections_preview(chunks: list[NodeWithScore]) -> str:
    if not chunks:
        return "none"
    labels: list[str] = []
    for c in chunks[:8]:
        meta = c.node.metadata or {}
        labels.append(str(meta.get("chunk_source_collection", "?")))
    return ",".join(labels)


async def run_query(query: str, top_k: int) -> OrchestratorResult:
    plog("run_query start top_k=%s q_preview=%s", top_k, (query[:160] + "…") if len(query) > 160 else query)

    async with timed_async("classify_query"):
        query_type = classify_query(query)

    async with timed_async("embed_query"):
        query_embedding = await embed_query(query)

    plog("run_query classified query_type=%s embed_dim=%s", query_type, len(query_embedding))

    serial_parent_doc: dict[str, Any] | None = None
    serial_parent_id: Any | None = None
    used_serial_fallback = False

    if query_type == "serial_number":
        serial_number = extract_serial_number(query)
        if serial_number:
            serial_parent_doc = find_parent_firearm_by_serial(serial_number)
            if serial_parent_doc is not None:
                serial_parent_id = serial_parent_doc.get("_id")
                plog("serial lookup hit _id=%s", serial_parent_id)
            else:
                used_serial_fallback = True
                plog("serial lookup miss for %s — semantic fallback", serial_number)

    async with timed_async("retrieve"):
        chunks = await retrieve(
            query,
            query_type,
            top_k,
            query_embedding,
            serial_parent_id=serial_parent_id,
        )
    if query_type == "serial_number" and serial_parent_doc is not None and not chunks:
        serial_source_id = str(serial_parent_doc["_id"])
        summary_parts = [
            f"Model: {serial_parent_doc.get('model') or 'Unknown'}",
            f"Serial Number: {serial_parent_doc.get('serial_number') or 'Unknown'}",
        ]
        if serial_parent_doc.get("year") is not None:
            summary_parts.append(f"Year: {serial_parent_doc.get('year')}")
        elif serial_parent_doc.get("estimated_year") is not None:
            summary_parts.append(f"Estimated Year: {serial_parent_doc.get('estimated_year')}")
        if serial_parent_doc.get("finish"):
            summary_parts.append(f"Finish: {serial_parent_doc.get('finish')}")
        if serial_parent_doc.get("factory_letter"):
            summary_parts.append("Factory letter on file.")
        synthetic_node = TextNode(
            text=". ".join(summary_parts),
            metadata={
                "chunk_source_collection": "firearms_direct_lookup",
                "source_firearm_id": serial_source_id,
            },
        )
        chunks = [NodeWithScore(node=synthetic_node, score=1.0)]

    plog("run_query chunks=%s collections_preview=%s", len(chunks), _chunk_collections_preview(chunks))

    if serial_parent_doc is not None:
        parent_docs = {str(serial_parent_doc["_id"]): serial_parent_doc}
    else:
        source_ids: list[str] = []
        for chunk in chunks:
            source_id = chunk.node.metadata.get("source_firearm_id")
            if (
                _is_firearms_chunk(chunk)
                and source_id
                and str(source_id) not in source_ids
            ):
                source_ids.append(str(source_id))
        parent_docs = fetch_parent_firearms(source_ids)
    image_refs = build_image_refs(parent_docs)
    source_meta = build_source_meta(chunks, parent_docs)
    user_prompt = build_user_prompt(query, chunks, parent_docs, len(image_refs))
    async with timed_async("anthropic_narration"):
        narration_text = await synthesize_narration(user_prompt)

    plog(
        "run_query done narration_chars=%s parent_docs=%s images=%s",
        len(narration_text),
        len(parent_docs),
        len(image_refs),
    )

    collections_hit = sorted(
        {
            str((chunk.node.metadata or {}).get("chunk_source_collection", "unknown"))
            for chunk in chunks
            if (chunk.node.metadata or {}).get("chunk_source_collection")
        }
    )
    if query_type == "serial_number" and used_serial_fallback:
        collections_hit.append("serial_fallback_semantic")

    return OrchestratorResult(
        narration_text=narration_text,
        image_count=len(image_refs),
        image_refs=image_refs,
        source_meta=source_meta,
        confidence=source_meta.get("confidence", 0.0),
        query_type=query_type,
        collections_hit=collections_hit,
    )
