from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateExportsStorage(FileSystemStorage):
    """Filesystem storage for generated PDFs.

    Located outside MEDIA_ROOT so the media-serve URL route and any reverse-
    proxy alias for /media/ cannot reach these files.  Downloads must go
    through ExportJobViewSet.result, which enforces authentication.
    """

    def __init__(self):
        super().__init__(location=settings.EXPORTS_ROOT, base_url=None)
