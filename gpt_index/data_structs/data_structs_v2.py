"""Data structures v2.

Nodes are decoupled from the indices.

"""

import uuid
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from dataclasses_json import DataClassJsonMixin
from pydantic import Json

from gpt_index.constants import DATA_KEY, TYPE_KEY
from gpt_index.data_structs.node_v2 import Node
from gpt_index.data_structs.struct_type import IndexStructType


@dataclass
class V2IndexStruct(DataClassJsonMixin):
    """A base data struct for a LlamaIndex."""

    index_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    summary: Optional[str] = None

    def get_summary(self) -> str:
        """Get text summary."""
        if self.summary is None:
            raise ValueError("summary field of the index_struct not set.")
        return self.summary

    @classmethod
    @abstractmethod
    def get_type(cls) -> IndexStructType:
        """Get index struct type."""

    def to_dict(self, encode_json: bool = False) -> Dict[str, Json]:
        out_dict = {
            TYPE_KEY: self.get_type(),
            DATA_KEY: super().to_dict(encode_json),
        }
        return out_dict


@dataclass
class IndexGraph(V2IndexStruct):
    """A graph representing the tree-structured index."""

    # mapping from index in tree to Node doc id.
    all_nodes: Dict[int, str] = field(default_factory=dict)
    root_nodes: Dict[int, str] = field(default_factory=dict)
    node_id_to_children_ids: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def node_id_to_index(self) -> Dict[str, int]:
        """Map from node id to index."""
        return {node_id: index for index, node_id in self.all_nodes.items()}

    @property
    def size(self) -> int:
        """Get the size of the graph."""
        return len(self.all_nodes)

    def get_index(self, node: Node) -> int:
        """Get index of node."""
        return self.node_id_to_index[node.get_doc_id()]

    def insert(
        self,
        node: Node,
        index: Optional[int] = None,
        children_nodes: Optional[Sequence[Node]] = None,
    ) -> None:
        """Insert node."""
        index = index or self.size
        node_id = node.get_doc_id()

        self.all_nodes[index] = node_id

        if children_nodes is None:
            children_nodes = []
        children_ids = [n.get_doc_id() for n in children_nodes]
        self.node_id_to_children_ids[node_id] = children_ids

    def get_children(self, parent_node: Optional[Node]) -> Dict[int, str]:
        """Get children nodes."""
        if parent_node is None:
            return self.root_nodes
        else:
            parent_id = parent_node.get_doc_id()
            children_ids = self.node_id_to_children_ids[parent_id]
            return {
                self.node_id_to_index[child_id]: child_id for child_id in children_ids
            }

    def insert_under_parent(
        self, node: Node, parent_node: Optional[Node], new_index: Optional[int] = None
    ) -> None:
        """Insert under parent node."""
        new_index = new_index or self.size
        if parent_node is None:
            self.root_nodes[new_index] = node.get_doc_id()
        else:
            if parent_node.doc_id not in self.node_id_to_children_ids:
                self.node_id_to_children_ids[parent_node.get_doc_id()] = []
            self.node_id_to_children_ids[parent_node.get_doc_id()].append(
                node.get_doc_id()
            )

        self.all_nodes[new_index] = node.get_doc_id()

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.TREE


@dataclass
class KeywordTable(V2IndexStruct):
    """A table of keywords mapping keywords to text chunks."""

    table: Dict[str, Set[str]] = field(default_factory=dict)

    def add_node(self, keywords: List[str], node: Node) -> None:
        """Add text to table."""
        for keyword in keywords:
            if keyword not in self.table:
                self.table[keyword] = set()
            self.table[keyword].add(node.get_doc_id())

    @property
    def node_ids(self) -> Set[str]:
        """Get all node ids."""
        return set.union(*self.table.values())

    @property
    def keywords(self) -> Set[str]:
        """Get all keywords in the table."""
        return set(self.table.keys())

    @property
    def size(self) -> int:
        """Get the size of the table."""
        return len(self.table)

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.KEYWORD_TABLE


@dataclass
class IndexList(V2IndexStruct):
    """A list of documents."""

    nodes: List[str] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        """Add text to table, return current position in list."""
        # don't worry about child indices for now, nodes are all in order
        self.nodes.append(node.get_doc_id())

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.LIST


@dataclass
class IndexDict(V2IndexStruct):
    """A simple dictionary of documents."""

    # mapping from vector store id to node id
    nodes_dict: Dict[str, str] = field(default_factory=dict)
    # mapping from doc_id to vector store id
    doc_id_dict: Dict[str, List[str]] = field(default_factory=dict)

    # TODO: temporary hack to store embeddings for simple vector index
    # this should be empty for all other indices
    embeddings_dict: Dict[str, List[float]] = field(default_factory=dict)

    def add_node(
        self,
        node: Node,
        text_id: Optional[str] = None,
    ) -> str:
        """Add text to table, return current position in list."""
        # # don't worry about child indices for now, nodes are all in order
        # self.nodes_dict[int_id] = node
        vector_id = text_id if text_id is not None else node.get_doc_id()
        self.nodes_dict[vector_id] = node.get_doc_id()
        if node.ref_doc_id is not None:
            if node.ref_doc_id not in self.doc_id_dict:
                self.doc_id_dict[node.ref_doc_id] = []
            self.doc_id_dict[node.ref_doc_id].append(vector_id)

        return vector_id

    def delete(self, doc_id: str) -> None:
        """Delete a Node."""
        if doc_id not in self.doc_id_dict:
            return
        for vector_id in self.doc_id_dict[doc_id]:
            del self.nodes_dict[vector_id]
        del self.doc_id_dict[doc_id]

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.VECTOR_STORE


@dataclass
class KG(V2IndexStruct):
    """A table of keywords mapping keywords to text chunks."""

    # Unidirectional

    table: Dict[str, Set[str]] = field(default_factory=dict)
    # text_chunks: Dict[str, Node] = field(default_factory=dict)
    rel_map: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    embedding_dict: Dict[str, List[float]] = field(default_factory=dict)

    @property
    def node_ids(self) -> Set[str]:
        """Get all node ids."""
        return set.union(*self.table.values())

    def add_to_embedding_dict(self, triplet_str: str, embedding: List[float]) -> None:
        """Add embedding to dict."""
        self.embedding_dict[triplet_str] = embedding

    def upsert_triplet(self, triplet: Tuple[str, str, str]) -> None:
        """Upsert a knowledge triplet to the graph."""
        subj, relationship, obj = triplet
        if subj not in self.rel_map:
            self.rel_map[subj] = []
        self.rel_map[subj].append((obj, relationship))

    def add_node(self, keywords: List[str], node: Node) -> None:
        """Add text to table."""
        node_id = node.get_doc_id()
        for keyword in keywords:
            if keyword not in self.table:
                self.table[keyword] = set()
            self.table[keyword].add(node_id)
        # self.text_chunks[node_id] = node

    def get_rel_map_texts(self, keyword: str) -> List[str]:
        """Get the corresponding knowledge for a given keyword."""
        # NOTE: return a single node for now
        if keyword not in self.rel_map:
            return []
        texts = []
        for obj, rel in self.rel_map[keyword]:
            texts.append(str((keyword, rel, obj)))
        return texts

    def get_rel_map_tuples(self, keyword: str) -> List[Tuple[str, str]]:
        """Get the corresponding knowledge for a given keyword."""
        # NOTE: return a single node for now
        if keyword not in self.rel_map:
            return []
        return self.rel_map[keyword]

    def get_node_ids(self, keyword: str, depth: int = 1) -> List[str]:
        """Get the corresponding knowledge for a given keyword."""
        if depth > 1:
            raise ValueError("Depth > 1 not supported yet.")
        if keyword not in self.table:
            return []
        keywords = [keyword]
        # some keywords may correspond to a leaf node, may not be in rel_map
        if keyword in self.rel_map:
            keywords.extend([child for child, _ in self.rel_map[keyword]])

        node_ids: List[str] = []
        for keyword in keywords:
            for node_id in self.table.get(keyword, set()):
                node_ids.append(node_id)
            # TODO: Traverse (with depth > 1)
        return node_ids

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.KG


# TODO: remove once we centralize UX around vector index


@dataclass
class SimpleIndexDict(IndexDict):
    """Index dict for simple vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.SIMPLE_DICT


@dataclass
class FaissIndexDict(IndexDict):
    """Index dict for Faiss vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.DICT


@dataclass
class WeaviateIndexDict(IndexDict):
    """Index dict for Weaviate vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.WEAVIATE


@dataclass
class PineconeIndexDict(IndexDict):
    """Index dict for Pinecone vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.PINECONE


@dataclass
class QdrantIndexDict(IndexDict):
    """Index dict for Qdrant vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.QDRANT


@dataclass
class MilvusIndexDict(IndexDict):
    """Index dict for Milvus vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.MILVUS


@dataclass
class ChromaIndexDict(IndexDict):
    """Index dict for Chroma vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.CHROMA


@dataclass
class OpensearchIndexDict(IndexDict):
    """Index dict for Opensearch vector index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.OPENSEARCH


class ChatGPTRetrievalPluginIndexDict(IndexDict):
    """Index dict for ChatGPT Retrieval Plugin."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.CHATGPT_RETRIEVAL_PLUGIN


@dataclass
class EmptyIndex(IndexDict):
    """Empty index."""

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.EMPTY


@dataclass
class CompositeIndex(V2IndexStruct):
    all_index_structs: Dict[str, V2IndexStruct] = field(default_factory=dict)
    root_id: Optional[str] = None

    @classmethod
    def get_type(cls) -> IndexStructType:
        """Get type."""
        return IndexStructType.COMPOSITE

    def to_dict(self, encode_json: bool = False) -> Dict[str, Json]:
        data_dict = {
            "all_index_structs": {
                id_: struct.to_dict(encode_json=encode_json)
                for id_, struct in self.all_index_structs.items()
            },
            "root_id": self.root_id,
        }

        out_dict = {
            TYPE_KEY: self.get_type(),
            DATA_KEY: data_dict,
        }
        return out_dict
