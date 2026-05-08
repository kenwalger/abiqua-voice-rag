"""
LlamaIndex MongoDB vector store passes bson.ObjectId as TextNode.id_; Pydantic v2
requires a string. Patch query() before indexes are built (see orchestrator import order).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PATCHED = False


def apply_llama_mongodb_objectid_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from llama_index.core.schema import TextNode
    from llama_index.core.vector_stores.types import (
        VectorStoreQuery,
        VectorStoreQueryResult,
    )
    from llama_index.vector_stores.mongodb.base import (
        MongoDBAtlasVectorSearch,
        legacy_metadata_dict_to_node,
        metadata_dict_to_node,
    )

    def query(self: MongoDBAtlasVectorSearch, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        pipeline = self._create_query_pipeline(query)
        logger.debug("Running query pipeline: %s", pipeline)
        cursor = self._collection.aggregate(pipeline)

        top_k_nodes: list[Any] = []
        top_k_ids: list[str] = []
        top_k_scores: list[float] = []
        for res in cursor:
            text = res.pop(self._text_key)
            score = res.pop("score")
            doc_id = res.pop(self._id_key)
            id_str = str(doc_id)
            metadata_dict = res.pop(self._metadata_key)

            try:
                node = metadata_dict_to_node(metadata_dict)
                node.set_content(text)
                nid = getattr(node, "id_", None)
                if nid is not None and not isinstance(nid, str):
                    node.id_ = str(nid)
            except Exception:
                metadata, node_info, relationships = legacy_metadata_dict_to_node(
                    metadata_dict
                )
                node = TextNode(
                    text=text,
                    id_=id_str,
                    metadata=metadata,
                    start_char_idx=node_info.get("start", None),
                    end_char_idx=node_info.get("end", None),
                    relationships=relationships,
                )

            top_k_ids.append(id_str)
            top_k_nodes.append(node)
            top_k_scores.append(score)

        return VectorStoreQueryResult(
            nodes=top_k_nodes, similarities=top_k_scores, ids=top_k_ids
        )

    MongoDBAtlasVectorSearch.query = query  # type: ignore[method-assign]
    _PATCHED = True
