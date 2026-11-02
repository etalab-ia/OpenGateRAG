from dataclasses import dataclass


@dataclass
class PublicCollectionNotAllowedError:
    user_id: int


@dataclass
class CollectionNotFoundError:
    collection_id: int
