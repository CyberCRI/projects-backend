from drf_spectacular.extensions import OpenApiAuthenticationExtension


class BearerTokenScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.ProjectJWTAuthentication"
    name = "Bearer token auth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "Bearer",
            "in": "header",
            "name": "Authorization",
        }
