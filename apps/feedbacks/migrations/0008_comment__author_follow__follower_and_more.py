# Generated by Django 4.2.7 on 2023-12-06 15:09

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models
import django.db.models.deletion


def migrate_comments(apps, schema_editor):
    Comment = apps.get_model("feedbacks", "Comment")
    HistoricalComment = apps.get_model("feedbacks", "HistoricalComment")
    for comment in Comment.objects.all():
        Comment.objects.filter(pk=comment.pk).update(_author=comment.author)
    for historical_comment in HistoricalComment.objects.all():
        try:
            HistoricalComment.objects.filter(
                pk=historical_comment.pk
            ).update(_author=historical_comment.author)
        except ObjectDoesNotExist:
            historical_comment.delete()


def migrate_comments_reverse(apps, schema_editor):
    Comment = apps.get_model("feedbacks", "Comment")
    HistoricalComment = apps.get_model("feedbacks", "HistoricalComment")
    for comment in Comment.objects.all():
        Comment.objects.filter(pk=comment.pk).update(author=comment._author)
    for historical_comment in HistoricalComment.objects.all():
        try:
            HistoricalComment.objects.filter(
                pk=historical_comment.pk
            ).update(author=historical_comment._author)
        except ObjectDoesNotExist:
            historical_comment.delete()


def migrate_reviews(apps, schema_editor):
    Review = apps.get_model("feedbacks", "Review")
    for review in Review.objects.all():
        Review.objects.filter(pk=review.pk).update(_reviewer=review.reviewer)


def migrate_reviews_reverse(apps, schema_editor):
    Review = apps.get_model("feedbacks", "Review")
    for review in Review.objects.all():
        Review.objects.filter(pk=review.pk).update(reviewer=review._reviewer)


def migrate_follows(apps, schema_editor):
    Follow = apps.get_model("feedbacks", "Follow")
    HistoricalFollow = apps.get_model("feedbacks", "HistoricalFollow")
    for follow in Follow.objects.all():
        Follow.objects.filter(pk=follow.pk).update(_follower=follow.follower)
    for historical_follow in HistoricalFollow.objects.all():
        try:
            HistoricalFollow.objects.filter(
                pk=historical_follow.pk
            ).update(_follower=historical_follow.follower)
        except ObjectDoesNotExist:
            historical_follow.delete()


def migrate_follows_reverse(apps, schema_editor):
    Follow = apps.get_model("feedbacks", "Follow")
    HistoricalFollow = apps.get_model("feedbacks", "HistoricalFollow")
    for follow in Follow.objects.all():
        Follow.objects.filter(pk=follow.pk).update(follower=follow._follower)
    for historical_follow in HistoricalFollow.objects.all():
        try:
            HistoricalFollow.objects.filter(
                pk=historical_follow.pk
            ).update(follower=historical_follow._follower)
        except ObjectDoesNotExist:
            historical_follow.delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("feedbacks", "0007_follow_unique_follow"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="_author",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="follow",
            name="_follower",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="_follows",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="historicalcomment",
            name="_author",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="historicalfollow",
            name="_follower",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="_reviewer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(migrate_comments, migrate_comments_reverse),
        migrations.RunPython(migrate_reviews, migrate_reviews_reverse),
        migrations.RunPython(migrate_follows, migrate_follows_reverse),
        migrations.RemoveField(
            model_name="comment",
            name="author",
        ),
        migrations.RemoveField(
            model_name="historicalcomment",
            name="author",
        ),
        migrations.RemoveField(
            model_name="follow",
            name="follower",
        ),
        migrations.RemoveField(
            model_name="historicalfollow",
            name="follower",
        ),
        migrations.RemoveField(
            model_name="review",
            name="reviewer",
        ),
        migrations.RenameField(
            model_name="comment",
            old_name="_author",
            new_name="author",
        ),
        migrations.RenameField(
            model_name="follow",
            old_name="_follower",
            new_name="follower",
        ),
        migrations.RenameField(
            model_name="historicalcomment",
            old_name="_author",
            new_name="author",
        ),
        migrations.RenameField(
            model_name="historicalfollow",
            old_name="_follower",
            new_name="follower",
        ),
        migrations.RenameField(
            model_name="review",
            old_name="_reviewer",
            new_name="reviewer",
        ),
        migrations.AlterField(
            model_name="comment",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="follow",
            name="follower",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="follows",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalcomment",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_constraint=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalfollow",
            name="follower",
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_constraint=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="reviewer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
