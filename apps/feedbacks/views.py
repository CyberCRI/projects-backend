import uuid

from django.db import transaction
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from simple_history.utils import update_change_reason

from apps.accounts.models import ProjectUser
from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.accounts.utils import get_user_id_field
from apps.commons.permissions import IsOwner
from apps.commons.utils.permissions import map_action_to_permission
from apps.commons.views import CreateListDestroyViewSet, MultipleIDViewsetMixin
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.notifications.tasks import notify_new_comment, notify_new_review
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission

from .filters import ReviewFilter
from .models import Comment, Follow, Review
from .permissions import IsReviewable
from .serializers import (
    CommentSerializer,
    FollowSerializer,
    ReviewSerializer,
    UserFollowManySerializer,
)


class ReviewViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    multiple_lookup_fields = ["user_id"]

    def get_user_id_from_lookup_value(self, lookup_value):
        lookup_field = get_user_id_field(lookup_value)
        if lookup_field != "id":
            user = get_object_or_404(
                ProjectUser.objects.all(), **{lookup_field: lookup_value}
            )
            return user.id
        return lookup_value

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "review")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                IsReviewable,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "feedbacks")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.get_project_related_queryset(Review.objects.all())
        if self.request.user.is_authenticated:
            qs = (qs | Review.objects.filter(reviewer=self.request.user)).distinct()
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            qs = qs.filter(project=self.kwargs["project_id"])
        elif "user_id" in self.kwargs:
            qs = qs.filter(reviewer__id=self.kwargs["user_id"])
        return qs.select_related("reviewer")

    def perform_create(self, serializer):
        review = serializer.save(reviewer=self.request.user)
        notify_new_review.delay(review.id)


class FollowViewSet(MultipleIDViewsetMixin, CreateListDestroyViewSet):
    serializer_class = FollowSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    multiple_lookup_fields = ["user_id"]

    def get_user_id_from_lookup_value(self, lookup_value):
        lookup_field = get_user_id_field(lookup_value)
        if lookup_field != "id":
            user = get_object_or_404(
                ProjectUser.objects.all(), **{lookup_field: lookup_value}
            )
            return user.id
        return lookup_value

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "follow")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "feedbacks")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.get_project_related_queryset(Follow.objects.all())
        if self.request.user.is_authenticated:
            qs = (qs | Follow.objects.filter(follower=self.request.user)).distinct()
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            qs = qs.filter(project=self.kwargs["project_id"])
        elif "user_id" in self.kwargs:
            qs = qs.filter(follower__id=self.kwargs["user_id"])
        return qs.select_related("follower")

    def check_linked_project_permission(self, project):
        # TODO : django-guardian rework this is weird
        if not self.request.user.can_see_project(project):
            self.permission_denied(self.request, code=403)

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        self.check_linked_project_permission(project)
        serializer.save(follower=self.request.user)


class UserFollowViewSet(FollowViewSet):
    @extend_schema(request=UserFollowManySerializer, responses=FollowSerializer)
    @action(
        detail=False,
        methods=["POST"],
        url_name="follow-many",
        url_path="follow-many",
        # TODO : maybe a better permission check here ?
        permission_classes=[AllowAny],
    )
    def follow_many(self, request, *args, **kwargs):
        serializer = UserFollowManySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO do we have to check the permission of the user making the request or the user following the projects? probably the same anyway
        user = ProjectUser.objects.get(id=kwargs["user_id"])
        with transaction.atomic():
            for follow in serializer.validated_data["follows"]:
                self.check_linked_project_permission(follow["project"])
                Follow.objects.create(project=follow["project"], follower=user)
        context = {"request": request}
        return Response(
            FollowSerializer(
                Follow.objects.filter(follower=user),
                context=context,
                many=True,
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectFollowViewSet(FollowViewSet):
    pass


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "comment")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "feedbacks")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.get_project_related_queryset(Comment.objects.all())
        if self.request.user.is_authenticated:
            qs = (qs | Comment.objects.filter(author=self.request.user)).distinct()
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            qs = qs.filter(project=self.kwargs["project_id"])
        if self.action in ["retrieve", "list"]:
            qs = qs.exclude(
                Q(reply_on__isnull=False)
                | (Q(deleted_at__isnull=False) & Q(replies=None))
            )
        return qs.select_related("author").prefetch_related("replies")

    def create(self, request, *args, **kwargs):

        # TODO : handle with MultipleIDViewsetMixin
        project = Project.objects.filter(slug=self.kwargs["project_id"])
        if project.exists():
            self.kwargs["project_id"] = project.get().id

        get_object_or_404(
            self.request.user.get_project_queryset(), id=self.kwargs["project_id"]
        )
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        notify_new_comment.delay(comment.id)
        update_change_reason(comment.project, "Added comment")

    @transaction.atomic
    def perform_destroy(self, instance: Comment):
        instance.soft_delete(self.request.user)
        instance.project._change_reason = "Deleted comment"
        instance.project.save()

    @transaction.atomic
    def perform_update(self, serializer):
        comment = serializer.save()
        update_change_reason(comment.project, "Updated comment")


class CommentImagesView(ImageStorageView):
    def get_permissions(self):
        """
        Permissions are handled differently here because contrary to other
        images endpoints, the users that can post images are not the same
        as the users that can update or remove them.
        """
        codename = map_action_to_permission(self.action, "comment")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "feedbacks")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        qs = self.request.user.get_project_related_queryset(
            Image.objects.all(), project_related_name="comments__project"
        )
        if self.request.user.is_authenticated:
            qs = (qs | Image.objects.filter(owner=self.request.user)).distinct()
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            qs = qs.filter(comments__project=self.kwargs["project_id"])
        if self.action in ["retrieve", "list"]:
            qs = qs.exclude(
                Q(comments__reply_on__isnull=False)
                | (Q(comments__deleted_at__isnull=False) & Q(comments__replies=None))
            )
        return qs

    def create(self, request, *args, **kwargs):

        # TODO : handle with MultipleIDViewsetMixin
        project = Project.objects.filter(slug=self.kwargs["project_id"])
        if project.exists():
            self.kwargs["project_id"] = project.get().id

        get_object_or_404(
            self.request.user.get_project_queryset(), id=self.kwargs["project_id"]
        )
        return super().create(request, *args, **kwargs)

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"comment/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "project_id" in self.kwargs:
            return f"/v1/project/{self.kwargs['project_id']}/comment-image/{image.id}"
        return None

    class Meta:
        additional_actions = ("image",)
