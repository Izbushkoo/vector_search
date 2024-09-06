import copy
from typing import Dict, Optional, List, Any, Tuple, Type, Union

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from global_utils import tokens_from_string


class CustomSplitterV2(RecursiveCharacterTextSplitter):

    def create_documents(
            self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[Document]:
        """Create documents from a list of texts."""
        _metadatas = metadatas or [{}] * len(texts)
        documents = []
        for i, text in enumerate(texts):
            index = -1
            for chunk in self.split_text(text):
                metadata = copy.deepcopy(_metadatas[i])
                if self._add_start_index:
                    index = text.find(chunk, index + 1)
                    metadata["start_index"] = index
                if len(chunk) > 30:
                    new_doc = Document(page_content=chunk, metadata=metadata)
                    documents.append(new_doc)

        return documents

    def create_documents_with_metadata(self, metadata):
        new_metadata = {}
        new_text = metadata["content"]
        new_metadata["id"] = metadata["id"]
        new_metadata["signature"] = metadata["signature"]
        new_metadata["keywords"] = metadata["keywords"]
        return self.create_documents(
            [new_text], metadatas=[new_metadata]
        )

    @staticmethod
    def create_single_document_with_metadata(metadata):
        new_metadata = {}
        new_text = metadata["content"]
        new_metadata["id"] = metadata["id"]
        new_metadata["signature"] = metadata["signature"]
        new_metadata["keywords"] = metadata["keywords"]
        new_metadata["title"] = metadata["title"]
        return [Document(
            page_content=new_text, metadata=new_metadata
        )]

    @staticmethod
    def create_title_document(metadata) -> List[Document]:
        return [Document(
            page_content=metadata["title"],
            metadata={
                "id": metadata["id"]
            }
        )]


splitter = CustomSplitterV2(
    chunk_size=1200,
    chunk_overlap=0,
    length_function=tokens_from_string
)