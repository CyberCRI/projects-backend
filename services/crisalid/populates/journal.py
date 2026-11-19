from services.crisalid.models import Journal, JournalIdentifier

from .base import AbstractPopulate
from .logger import logger


class PopulateJournal(AbstractPopulate):
    """Populate journals from crisalid "journals" query (no relations)"""

    def node(self, data: dict) -> Journal | None:
        uid = self.sanitize_string(data.get("uid"))
        identifiers = self.sanitize_identifiers(
            JournalIdentifier, data.get("identifiers")
        )
        # uids can be the same in two crisalid instances, journals are matched by identifiers
        if not identifiers:
            logger.warning("Journal %r without identifiers", uid)
            return None

        journal = self.cache.from_identifiers(Journal, identifiers)
        titles = [title for title in data.get("titles") or [] if title]
        self.cache.save(
            journal, title=self.sanitize_string(titles[0] if titles else uid)
        )
        self.save_identifiers(journal, identifiers)
        return journal
