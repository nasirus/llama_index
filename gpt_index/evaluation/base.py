"""Evaluating the responses from an index."""
from __future__ import annotations

from typing import List, Optional

from gpt_index import (
    Document,
    GPTListIndex,
    QuestionAnswerPrompt,
    RefinePrompt,
    Response,
    ServiceContext,
)

DEFAULT_EVAL_PROMPT = (
    "Please tell if a given piece of information "
    "is supported by the context.\n"
    "You need to answer with either YES or NO.\n"
    "Answer YES if any of the context supports the information, even "
    "if most of the context is unrelated. "
    "Some examples are provided below. \n\n"
    "Information: Apple pie is generally double-crusted.\n"
    "Context: An apple pie is a fruit pie in which the principal filling "
    "ingredient is apples. \n"
    "Apple pie is often served with whipped cream, ice cream "
    "('apple pie à la mode'), custard or cheddar cheese.\n"
    "It is generally double-crusted, with pastry both above "
    "and below the filling; the upper crust may be solid or "
    "latticed (woven of crosswise strips).\n"
    "Answer: YES\n"
    "Information: Apple pies tastes bad.\n"
    "Context: An apple pie is a fruit pie in which the principal filling "
    "ingredient is apples. \n"
    "Apple pie is often served with whipped cream, ice cream "
    "('apple pie à la mode'), custard or cheddar cheese.\n"
    "It is generally double-crusted, with pastry both above "
    "and below the filling; the upper crust may be solid or "
    "latticed (woven of crosswise strips).\n"
    "Answer: NO\n"
    "Information: {query_str}\n"
    "Context: {context_str}\n"
    "Answer: "
)

DEFAULT_REFINE_PROMPT = (
    "We want to understand if the following information is present "
    "in the context information: {query_str}\n"
    "We have provided an existing YES/NO answer: {existing_answer}\n"
    "We have the opportunity to refine the existing answer "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "If the existing answer was already YES, still answer YES. "
    "If the information is present in the new context, answer YES. "
    "Otherwise answer NO.\n"
)

QUERY_RESPONSE_EVAL_PROMPT = (
    "Your task is to evaluate if the response for the query \
    is in line with the context information provided.\n"
    "You have two options to answer. Either YES/ NO.\n"
    "Answer - YES, if the response for the query \
    is in line with context information otherwise NO.\n"
    "Query and Response: \n {query_str}\n"
    "Context: \n {context_str}\n"
    "Answer: "
)

QUERY_RESPONSE_REFINE_PROMPT = (
    "We want to understand if the following query and response is"
    "in line with the context information: \n {query_str}\n"
    "We have provided an existing YES/NO answer: \n {existing_answer}\n"
    "We have the opportunity to refine the existing answer "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "If the existing answer was already YES, still answer YES. "
    "If the information is present in the new context, answer YES. "
    "Otherwise answer NO.\n"
)


class ResponseEvaluator:
    """Evaluate based on response from indices.

    NOTE: this is a beta feature, subject to change!

    Args:
        service_context (Optional[ServiceContext]): ServiceContext object

    """

    def __init__(
        self,
        service_context: Optional[ServiceContext] = None,
    ) -> None:
        """Init params."""
        self.service_context = service_context or ServiceContext.from_defaults()

    def get_context(self, response: Response) -> List[Document]:
        """Get context information from given Response object using source nodes.

        Args:
            response (Response): Response object from an index based on the query.

        Returns:
            List of Documents of source nodes information as context information.
        """

        context = []

        for context_info in response.source_nodes:
            context.append(Document(context_info.source_text))

        return context

    def evaluate(self, response: Response) -> str:
        """Evaluate the response from an index.

        Args:
            query: Query for which response is generated from index.
            response: Response object from an index based on the query.
        Returns:
            Yes -> If answer, context information are matching \
                    or If Query, answer and context information are matching.
            No -> If answer, context information are not matching \
                    or If Query, answer and context information are not matching.
        """
        answer = str(response)

        context = self.get_context(response)
        index = GPTListIndex.from_documents(
            context, service_context=self.service_context
        )
        response_txt: str = ""

        EVAL_PROMPT_TMPL = QuestionAnswerPrompt(DEFAULT_EVAL_PROMPT)
        REFINE_PROMPT_TMPL = RefinePrompt(DEFAULT_REFINE_PROMPT)

        response_obj = index.query(
            answer,
            text_qa_template=EVAL_PROMPT_TMPL,
            refine_template=REFINE_PROMPT_TMPL,
        )
        response_txt = str(response_obj)

        return response_txt


class QueryResponseEvaluator:
    """Evaluate based on query and response from indices.

    NOTE: this is a beta feature, subject to change!

    Args:
        service_context (Optional[ServiceContext]): ServiceContext object

    """

    def __init__(
        self,
        service_context: Optional[ServiceContext] = None,
    ) -> None:
        """Init params."""
        self.service_context = service_context or ServiceContext.from_defaults()

    def get_context(self, response: Response) -> List[Document]:
        """Get context information from given Response object using source nodes.

        Args:
            response (Response): Response object from an index based on the query.

        Returns:
            List of Documents of source nodes information as context information.
        """

        context = []

        for context_info in response.source_nodes:
            context.append(Document(context_info.source_text))

        return context

    def evaluate(self, query: str, response: Response) -> str:
        """Evaluate the response from an index.

        Args:
            query: Query for which response is generated from index.
            response: Response object from an index based on the query.
        Returns:
            Yes -> If answer, context information are matching \
                    or If Query, answer and context information are matching.
            No -> If answer, context information are not matching \
                    or If Query, answer and context information are not matching.
        """
        answer = str(response)

        context = self.get_context(response)
        index = GPTListIndex.from_documents(
            context, service_context=self.service_context
        )
        response_txt: str = ""

        QUERY_RESPONSE_EVAL_PROMPT_TMPL = QuestionAnswerPrompt(
            QUERY_RESPONSE_EVAL_PROMPT
        )
        QUERY_RESPONSE_REFINE_PROMPT_TMPL = RefinePrompt(QUERY_RESPONSE_REFINE_PROMPT)

        query_response = f"Question: {query}\nResponse: {answer}"

        response_obj = index.query(
            query_response,
            text_qa_template=QUERY_RESPONSE_EVAL_PROMPT_TMPL,
            refine_template=QUERY_RESPONSE_REFINE_PROMPT_TMPL,
        )
        response_txt = str(response_obj)

        return response_txt
