from typing import Dict

from pydantic import BaseModel


class AwsBase(BaseModel):
    """Base class for configuration objects to pass to AWS component resources."""

    tags: Dict[str, str]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tags.update({"pulumi-managed": "true"})