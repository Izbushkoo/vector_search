import uuid
from typing import List, Optional, Dict
import logging
import os

from langchain.retrievers import MultiVectorRetriever, ParentDocumentRetriever

from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.retrievers.parent_document_retriever import ParentDocumentRetriever
from langchain_core.runnables.configurable import ConfigurableField
from langchain.storage import RedisStore, create_kv_docstore
from langchain.schema.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.schema import Document
from langchain.text_splitter import TextSplitter

from langchain.vectorstores import PGVector

from global_utils import tokens_from_string
from app.services.splitter import CustomSplitterV2
from app.services.models import model_selector, ModelName
from app.core.config import settings


class CustomMultiVectorRetriever(MultiVectorRetriever):

    @staticmethod
    def format_docs_to_log(docs: List[Document]):
        text = ""
        for idx, doc in enumerate(docs):
            text += f"  {idx + 1} ID: {doc.metadata.get('id')} - {doc.page_content}\n"
        return text

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Get documents relevant to a query.
        Args:
            query: String to find relevant documents for
            run_manager: The callbacks handler to use
        Returns:
            List of relevant documents
        """
        sub_docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
        # logger.info(f"Child docs were extracted for query **{query}**: \n {self.format_docs_to_log(sub_docs)}\n")
        # We do this to maintain the order of the ids that are returned
        ids = []
        for d in sub_docs:
            if d.metadata[self.id_key] not in ids:
                ids.append(d.metadata[self.id_key])
        docs = self.docstore.mget(ids)
        logging.info(f"Child docs were extracted for query **{query}**: \n {self.format_docs_to_log(docs)}\n")
        return [d for d in docs if d is not None]


class CustomParentDocumentRetriever(CustomMultiVectorRetriever):

    child_splitter: TextSplitter
    """The text splitter to use to create child documents."""

    """The key to use to track the parent id. This will be stored in the
    metadata of child documents."""
    parent_splitter: Optional[TextSplitter] = None
    """The text splitter to use to create parent documents.
    If none, then the parent documents will be the raw documents passed in."""

    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None,
        add_to_docstore: bool = True,
    ) -> None:
        """Adds documents to the docstore and vectorstores.

        Args:
            documents: List of documents to add
            ids: Optional list of ids for documents. If provided should be the same
                length as the list of documents. Can provided if parent documents
                are already in the document store and you don't want to re-add
                to the docstore. If not provided, random UUIDs will be used as
                ids.
            add_to_docstore: Boolean of whether to add documents to docstore.
                This can be false if and only if `ids` are provided. You may want
                to set this to False if the documents are already in the docstore
                and you don't want to re-add them.
        """
        if self.parent_splitter is not None:
            documents = self.parent_splitter.split_documents(documents)
        if ids is None:
            doc_ids = [str(uuid.uuid4()) for _ in documents]
            if not add_to_docstore:
                raise ValueError(
                    "If ids are not passed in, `add_to_docstore` MUST be True"
                )
        else:
            if len(documents) != len(ids):
                raise ValueError(
                    "Got uneven list of documents and ids. "
                    "If `ids` is provided, should be same length as `documents`."
                )
            doc_ids = ids

        docs = []
        full_docs = []
        for i, doc in enumerate(documents):
            _id = doc_ids[i]
            sub_docs = self.child_splitter.split_documents([doc])
            for _doc in sub_docs:
                _doc.metadata[self.id_key] = _id
            docs.extend(sub_docs)
            full_docs.append((_id, doc))
        self.vectorstore.add_documents(docs)
        if add_to_docstore:
            self.docstore.mset(full_docs)
            
            
def get_parent_retriever(collection_name: str, k: int = 6, score: float | int = 0.8):
    child_splitter = CustomSplitterV2(
        chunk_size=400,
        chunk_overlap=0,
        length_function=tokens_from_string
    )
    docstore = create_kv_docstore(RedisStore(redis_url="redis://redis:6379"))

    vectorstore = PGVector(
        collection_name=collection_name,
        connection_string=settings.PG_VECTOR_URI,
        embedding_function=model_selector(ModelName.embed)
    )

    return CustomParentDocumentRetriever(
        child_splitter=child_splitter,
        docstore=docstore,
        vectorstore=vectorstore,
        search_kwargs={
            "k": k,
            "score_threshold": score,
        }
    )

