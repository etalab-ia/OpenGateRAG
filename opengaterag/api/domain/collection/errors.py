from dataclasses import dataclass


@dataclass
class PublicCollectionNotAllowedError:
    user_id: int
