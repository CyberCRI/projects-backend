from django.db import models, transaction

from services.crisalid.models import AbstractIdentifier, CrisalidConfig


def _config_links(identifier_model: type[AbstractIdentifier]):
    """through model of identifiers <-> configs, with its identifier/config columns"""
    field = identifier_model._meta.get_field("configs")
    return field.remote_field.through, field.m2m_column_name(), field.m2m_reverse_name()


def link_identifiers(
    identifier_model: type[AbstractIdentifier], pks: list[int], config: CrisalidConfig
):
    """add the config to identifiers (if not already linked)"""
    through, column, config_column = _config_links(identifier_model)
    through.objects.bulk_create(
        [through(**{column: pk, config_column: config.pk}) for pk in pks],
        ignore_conflicts=True,
    )


def release_identifiers(queryset: models.QuerySet, config: CrisalidConfig):
    """remove the config from identifiers, delete identifiers without any config left"""
    through, column, config_column = _config_links(queryset.model)
    pks = list(queryset.values_list("pk", flat=True))
    with transaction.atomic():
        through.objects.filter(
            **{f"{column}__in": pks, config_column: config.pk}
        ).delete()
        queryset.model.objects.filter(pk__in=pks, configs__isnull=True).delete()


def release_instances(queryset: models.QuerySet, config: CrisalidConfig) -> list[int]:
    """remove the config from identifiers of the instances ("deleted" event of a config),
    instances without any identifier left are deleted

    :return: pks of deleted instances
    """
    fk = queryset.model.identifiers.field
    pks = list(queryset.values_list("pk", flat=True))
    with transaction.atomic():
        release_identifiers(fk.model.objects.filter(**{f"{fk.name}__in": pks}), config)
        orphans = list(
            queryset.model.objects.filter(
                pk__in=pks, identifiers__isnull=True
            ).values_list("pk", flat=True)
        )
        queryset.model.objects.filter(pk__in=orphans).delete()
    return orphans
