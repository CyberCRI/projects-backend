from locust import HttpUser, task
from requests_oauthlib import OAuth2Session

client_id = 'projects-frontend-dev'
client_secret = '***'
authorization_base_url = 'https://keycloak.k8s.lp-i.dev/realms/lp/protocol/openid-connect/auth'
token_url = 'https://keycloak.k8s.lp-i.dev/realms/lp/protocol/openid-connect/token'
redirect_uri = 'https://projects.k8s.lp-i.dev/'

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, pkce="S256")

authorization_url, state = oauth.authorization_url(
        authorization_base_url,
        # access_type and prompt are Google specific extra
        # parameters.
        )

print(f'Please go to {authorization_url} and authorize access.')

authorization_response = input('Enter the full callback URL')

token = oauth.fetch_token(token_url, authorization_response=authorization_response, client_secret=client_secret)

r = oauth.get("https://api.projects.k8s.lp-i.dev/v1/project/S5RjahkX/comment/")


class User(HttpUser):
    @task
    def get_people_group(self):
        self.client.get("/v1/organization/DEFAULT/people-group/ab-openlab/", headers={"Authorization": f"Bearer {token['access_token']}"})
