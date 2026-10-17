from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId


MUSCLE_GROUPS = ('CHEST', 'BACK', 'LEGS', 'ARMS', 'SHOULDERS', 'CORE', 'FULL_BODY')
EQUIPMENT = ('BARBELL', 'DUMBBELL', 'MACHINE', 'BODYWEIGHT', 'KETTLEBELL', 'RESISTANCE_BAND', 'OTHER')
NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 500


@dataclass
class Exercise:
    id: ObjectId
    name: str
    muscle_groups: list[str]
    equipment: list[str]
    created_at: datetime
    description: str | None = None
    video_url: str | None = None
    image_url: str | None = None

    @classmethod
    def from_document(cls, document: dict) -> 'Exercise':
        return cls(
            id=document.get('_id'), name=document.get('name'),
            muscle_groups=document.get('muscle_groups'), equipment=document.get('equipment'),
            created_at=document.get('created_at'), description=document.get('description'),
            video_url=document.get('video_url'), image_url=document.get('image_url'),
        )
