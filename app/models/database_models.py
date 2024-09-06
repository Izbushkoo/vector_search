from typing import Optional, List

from pydantic import BaseModel
import sqlmodel
from sqlmodel import SQLModel, Field
from sqlalchemy.dialects.postgresql.json import JSON



class CollectionsList(SQLModel, table=True):

    """Таблица используется для идентификации и предоставления списка существующих векторных коллекций.
    Поле 'contains_ids' содержит в себе список всех проиндексированных в данную коллекцию документов."""
    name: str = Field(primary_key=True, nullable=False)
    description: Optional[str] = Field(default=None, nullable=True)

    contains_ids: Optional[List[int]] = Field(default_factory=list, nullable=False, sa_column_kwargs={"type_": JSON})


