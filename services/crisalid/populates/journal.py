from services.crisalid.models import Journal

from .base import AbstractPopulate


class PopulateJournal(AbstractPopulate):
    """Populate journals from crisalid "journals" query (no relations)"""

    def node(self, data: dict) -> Journal | None:
        uid = self.sanitize_string(data.get("uid"))
        if not uid:
            return None
        journal = self.cache.model(Journal, uid=uid)
        titles = [title for title in data.get("titles") or [] if title]
        self.cache.save(
            journal, title=self.sanitize_string(titles[0] if titles else uid)
        )
        return journal
