from whitenoise.storage import CompressedManifestStaticFilesStorage


class RelaxedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    # jazzmin passes directory paths (e.g. 'vendor/bootswatch') to {% static %},
    # which ManifestStaticFilesStorage cannot resolve. Disabling strict mode
    # falls back to the unhashed path instead of raising ValueError.
    manifest_strict = False
