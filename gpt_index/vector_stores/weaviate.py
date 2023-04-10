"""Weaviate Vector store index.

An index that that is built on top of an existing vector store.

"""

from typing import Any, Dict, List, Optional, cast

from gpt_index.readers.weaviate.client import (
    add_nodes,
    create_schema,
    delete_document,
    weaviate_query,
)
from gpt_index.readers.weaviate.utils import get_default_class_prefix
from gpt_index.vector_stores.types import (
    NodeEmbeddingResult,
    VectorStore,
    VectorStoreQueryResult,
    VectorStoreQuery,
)


class WeaviateVectorStore(VectorStore):
    """Weaviate vector store.

    In this vector store, embeddings and docs are stored within a
    Weaviate collection.

    During query time, the index uses Weaviate to query for the top
    k most similar nodes.

    Args:
        weaviate_client (weaviate.Client): WeaviateClient
            instance from `weaviate-client` package
        class_prefix (Optional[str]): prefix for Weaviate classes

    """

    stores_text: bool = True

    def __init__(
        self,
        weaviate_client: Optional[Any] = None,
        class_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        import_err_msg = (
            "`weaviate` package not found, please run `pip install weaviate-client`"
        )
        try:
            import weaviate  # noqa: F401
            from weaviate import Client  # noqa: F401
        except ImportError:
            raise ImportError(import_err_msg)

        if weaviate_client is None:
            raise ValueError("Missing Weaviate client!")

        self._client = cast(Client, weaviate_client)
        # validate class prefix starts with a capital letter
        if class_prefix is not None and not class_prefix[0].isupper():
            raise ValueError(
                "Class prefix must start with a capital letter, e.g. 'Gpt'"
            )
        self._class_prefix = class_prefix or get_default_class_prefix()
        # try to create schema
        create_schema(self._client, self._class_prefix)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "VectorStore":
        if "weaviate_client" not in config_dict:
            raise ValueError("Missing Weaviate client!")
        return cls(**config_dict)

    @property
    def client(self) -> Any:
        """Get client."""
        return self._client

    @property
    def config_dict(self) -> dict:
        """Get config dict."""
        return {"class_prefix": self._class_prefix}

    def add(
        self,
        embedding_results: List[NodeEmbeddingResult],
    ) -> List[str]:
        """Add embedding results to index.

        Args
            embedding_results: List[NodeEmbeddingResult]: list of embedding results

        """
        for result in embedding_results:
            node = result.node
            embedding = result.embedding
            # TODO: always store embedding in node
            node.embedding = embedding

        add_nodes(self._client, [r.node for r in embedding_results], self._class_prefix)
        return [result.id for result in embedding_results]

    def delete(self, doc_id: str, **delete_kwargs: Any) -> None:
        """Delete a document.

        Args:
            doc_id (str): document id

        """
        delete_document(self._client, doc_id, self._class_prefix)

    def query(self, query: VectorStoreQuery) -> VectorStoreQueryResult:
        """Query index for top k most similar nodes."""
        nodes = weaviate_query(
            self._client,
            self._class_prefix,
            query,
        )
        nodes = nodes[: query.similarity_top_k]
        node_idxs = [str(i) for i in range(len(nodes))]

        return VectorStoreQueryResult(nodes=nodes, ids=node_idxs)
