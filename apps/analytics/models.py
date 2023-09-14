from django.db import models


class Stat(models.Model):
    project = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="stat"
    )
    comments = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)
    follows = models.IntegerField(default=0)
    links = models.IntegerField(default=0)
    files = models.IntegerField(default=0)
    blog_entries = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    versions = models.IntegerField(default=0)
    description_length = models.IntegerField(default=0)
    last_update = models.DateTimeField(auto_now=True)

    def update_comments_and_replies(self):
        self.comments = self.project.comments.filter(
            reply_on=None, deleted_at=None
        ).count()
        self.replies = (
            self.project.comments.filter(deleted_at=None).exclude(reply_on=None).count()
        )
        self.save()

    def update_follows(self):
        self.follows = self.project.follows.count()
        self.save()

    def update_links(self):
        self.links = self.project.links.count()
        self.save()

    def update_files(self):
        self.files = self.project.files.count()
        self.save()

    def update_blog_entries(self):
        self.blog_entries = self.project.blog_entries.count()
        self.save()

    def update_goals(self):
        self.goals = self.project.goals.count()
        self.save()

    def update_versions(self):
        self.versions = self.project.archive.count()
        self.save()

    def update_description_length(self):
        self.description_length = len(self.project.description)
        self.save()

    def update_all(self):
        self.update_comments_and_replies()
        self.update_follows()
        self.update_links()
        self.update_files()
        self.update_blog_entries()
        self.update_goals()
        self.update_versions()
        self.update_description_length()
        self.refresh_from_db()
        return self
