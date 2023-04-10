"""Struct store."""

import re
from typing import Any, Callable, Dict, Generic, Optional, Sequence, TypeVar

from gpt_index.data_structs.node_v2 import Node
from gpt_index.data_structs.table_v2 import BaseStructTable
from gpt_index.indices.base import BaseGPTIndex
from gpt_index.indices.service_context import ServiceContext
from gpt_index.prompts.default_prompts import DEFAULT_SCHEMA_EXTRACT_PROMPT
from gpt_index.prompts.prompts import SchemaExtractPrompt

BST = TypeVar("BST", bound=BaseStructTable)


def default_output_parser(output: str) -> Optional[Dict[str, Any]]:
    """Parse output of schema extraction.

    Attempt to parse the following format from the default prompt:
    field1: <value>, field2: <value>, ...

    """
    tups = output.split("\n")

    fields = {}
    for tup in tups:
        if ":" in tup:
            tokens = tup.split(":")
            field = re.sub(r"\W+", "", tokens[0])
            value = re.sub(r"\W+", "", tokens[1])
            fields[field] = value
    return fields


OUTPUT_PARSER_TYPE = Callable[[str], Optional[Dict[str, Any]]]


class BaseGPTStructStoreIndex(BaseGPTIndex[BST], Generic[BST]):
    """Base GPT Struct Store Index."""

    def __init__(
        self,
        nodes: Optional[Sequence[Node]] = None,
        index_struct: Optional[BST] = None,
        service_context: Optional[ServiceContext] = None,
        schema_extract_prompt: Optional[SchemaExtractPrompt] = None,
        output_parser: Optional[OUTPUT_PARSER_TYPE] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        self.schema_extract_prompt = (
            schema_extract_prompt or DEFAULT_SCHEMA_EXTRACT_PROMPT
        )
        self.output_parser = output_parser or default_output_parser
        super().__init__(
            nodes=nodes,
            index_struct=index_struct,
            service_context=service_context,
            **kwargs,
        )

    def _delete(self, doc_id: str, **delete_kwargs: Any) -> None:
        """Delete a document."""
        raise NotImplementedError("Delete not implemented for Struct Store Index.")
