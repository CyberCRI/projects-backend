from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .interface import GoogleService
from .serializers import EmailAvailableSerializer, EmailSerializer


class UserEmailAvailableView(APIView):
    @extend_schema(request=EmailSerializer, responses=EmailAvailableSerializer)
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_user = GoogleService.get_user_by_email(
            serializer.validated_data["email"]
        )
        return Response(
            EmailAvailableSerializer({"available": google_user is None}).data
        )


class GroupEmailAvailableView(APIView):
    @extend_schema(request=EmailSerializer, responses=EmailAvailableSerializer)
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_group = GoogleService.get_group_by_email(
            serializer.validated_data["email"]
        )
        return Response(
            EmailAvailableSerializer({"available": google_group is None}).data
        )


class OrgUnitsView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "string"}}})
    def get(self, request):
        return Response(GoogleService.get_org_units())
