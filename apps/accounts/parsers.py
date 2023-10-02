from rest_framework.parsers import DataAndFiles, MultiPartParser


class UserMultipartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        content = super().parse(
            stream, media_type=media_type, parser_context=parser_context
        )
        data = {
            key: self.list_to_value(key, value) for key, value in content.data.lists()
        }
        return DataAndFiles(data, content.files)

    def list_to_value(self, key, value):
        if key in ["sdgs", "roles_to_add", "roles_to_remove"]:
            return value
        return value[0]
