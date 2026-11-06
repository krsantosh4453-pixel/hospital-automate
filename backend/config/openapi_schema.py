"""
Default schema class for drf-spectacular. Kept apart from config/schema.py,
which imports DRF views: DRF loads this class while defining APIView.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView


class HMSAutoSchema(AutoSchema):
    """
    For hand-written APIViews without a serializer, document the body as a
    JSON object instead of logging "unable to guess serializer" for each one.
    Views with a serializer are documented exactly as before.
    """

    def _get_serializer(self):
        view = self.view
        own_class = getattr(view, "serializer_class", None)
        custom_getter = (hasattr(view, "get_serializer_class")
                         and type(view).get_serializer_class is not GenericAPIView.get_serializer_class)
        if not own_class and not custom_getter:
            return OpenApiTypes.OBJECT
        return super()._get_serializer()
