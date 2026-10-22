from django.shortcuts import get_object_or_404

from services.crisalid.models import Researcher


class NestedResearcherViewMixins:
    def initial(self, request, *args, **kwargs):
        self.researcher = get_object_or_404(
            Researcher,
            pk=kwargs["researcher_id"],
            user__groups__organizations__in=(self.organization,),
        )
        super().initial(request, *args, **kwargs)
