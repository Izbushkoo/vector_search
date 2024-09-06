

class CollectionExistsException(Exception):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.message = f"Collection already exists: '{collection_name}'"
        super().__init__(self.message)


class CollectionNotFoundException(Exception):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.message = f"Collection does not exists: '{collection_name}'"
        super().__init__(self.message)

