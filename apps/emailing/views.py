from django.shortcuts import redirect
from rest_framework import mixins, viewsets

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import ReadOnly
from apps.commons.utils import map_action_to_permission
from apps.emailing.serializers import EmailSerializer
from apps.files.models import Image
from apps.files.views import ImageStorageView

from .models import Email


class EmailImagesViewSet(ImageStorageView, mixins.RetrieveModelMixin):

    permission_classes = [ReadOnly]

    def get_queryset(self):
        if "email_id" in self.kwargs:
            return Image.objects.filter(emails__id=self.kwargs["email_id"])
        return Image.objects.none()

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)


class EmailViewSet(viewsets.ModelViewSet):
    serializer_class = EmailSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    queryset = Email.objects.all()

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "email")
        if codename:
            self.permission_classes = [HasBasePermission(codename, "emailing")]
        return super().get_permissions()
