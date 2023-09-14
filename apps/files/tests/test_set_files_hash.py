import hashlib
from io import StringIO

from django.core.management import call_command
from factory.django import FileField

from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentFileFactory


class SetFilesHashTestCase(JwtAPITestCase):
    @staticmethod
    def call_command():
        out = StringIO()
        call_command(
            "set_files_hash",
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def test_run_command(self):
        hash_a = hashlib.sha256(b"file a").hexdigest()
        hash_b = hashlib.sha256(b"file b").hexdigest()
        hash_c = hashlib.sha256(b"file c").hexdigest()
        file_a = AttachmentFileFactory(
            file=FileField(filename="file.txt", data=b"file a"), hashcode=""
        )
        file_b = AttachmentFileFactory(
            file=FileField(filename="file.txt", data=b"file b"), hashcode=""
        )
        file_c = AttachmentFileFactory(
            file=FileField(filename="file.txt", data=b"file a"), hashcode=hash_c
        )

        out = self.call_command()
        self.assertEqual(out, "Process finished, 2 files updated.\n", out)

        file_a.refresh_from_db()
        file_b.refresh_from_db()
        file_c.refresh_from_db()
        self.assertEqual(file_a.hashcode, hash_a)
        self.assertEqual(file_b.hashcode, hash_b)
        self.assertEqual(file_c.hashcode, hash_c)
