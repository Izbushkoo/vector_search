from typing import Optional

from pydantic import BaseModel, Field


class CollectionsListCreate(BaseModel):

    """Модель используется для создания идентификации коллекции. Поле 'contains_ids' отсутствует так как оно будет
    изменяться только в процессе обновления коллекции. Это позволит создавать коллекции без наполнения"""
    name: str
    descritption: Optional[str] = Field(default=None)
