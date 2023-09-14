from django.core.management import BaseCommand

from apps.projects.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        projects = Project.objects.all_with_delete()
        i = 0
        files_to_delete = []
        self.stdout.write("Looking for duplicated files")
        for project in projects:
            files_to_keep = []
            files = project.files
            for file in files.all():
                hashcode = file.hashcode
                if hashcode not in files_to_keep:
                    files_to_keep.append(hashcode)
                    i += 1
                else:
                    files_to_delete.append(file)
        proceed = ""
        while proceed not in ["y", "N"]:
            proceed = input(
                f"Delete {len(files_to_delete)} duplicated files and keep {i} unique files [yN]?"
            )
            if proceed == "y":
                for file in files_to_delete:
                    file.delete()
                self.stdout.write("File deletion over.")
            elif proceed == "N":
                self.stdout.write("File deletion interrupted.")
            else:
                self.stdout.write("Please enter a valid value. \n")
