from dataclasses import dataclass


@dataclass
class PublicCollectionNotAllowedError:
    pass


@dataclass
class CollectionNotFoundError:
    pass
