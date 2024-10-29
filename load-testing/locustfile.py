from locust import HttpUser, task
from requests_oauthlib import OAuth2Session
import os
import json
import base64

client_id = 'projects-frontend-dev'
client_secret = os.environ['CLIENT_SECRET']
authorization_base_url = 'https://keycloak.k8s.lp-i.dev/realms/lp/protocol/openid-connect/auth'
token_url = 'https://keycloak.k8s.lp-i.dev/realms/lp/protocol/openid-connect/token'
redirect_uri = 'https://projects.k8s.lp-i.dev/'

ORGANIZATION_CODE = 'DEFAULT'
GROUP_TO_TEST = 'testing_a6grj'
SEARCH_TERM = 'test'
USER_ID = '5e558735-5207-4c86-a3ed-c7f83b55e0e9'
PROJECT_TO_TEST = 'test-stan'

def prompt_login() -> str:
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, pkce="S256")
    authorization_url, state = oauth.authorization_url(
        authorization_base_url,
        # access_type and prompt are Google specific extra
        # parameters.
        )
    print(f'Please go to {authorization_url} and authorize access.')

    CALLBACK_URL = input('Enter the full callback URL')

    token = oauth.fetch_token(token_url, authorization_response=CALLBACK_URL, client_secret=client_secret)
    b64_token = base64.b64encode(bytes(json.dumps(token), "utf-8")).decode("utf-8")
    print(f'Token: {b64_token}. Please set this as an environment variable TOKEN for future runs.')
    return token


TOKEN = os.getenv('TOKEN', None)
if TOKEN is None:
    TOKEN= prompt_login()
else:
    TOKEN = json.loads(base64.b64decode(TOKEN))
    # Check if token is still valid
    oauth = OAuth2Session(client_id, token=TOKEN)
    oauth.refresh_token(token_url, client_id=client_id, client_secret=client_secret)

class User(HttpUser):

    def on_start(self):
        self.client.headers = {"Authorization": f"Bearer {TOKEN['access_token']}"}

    @task
    def get_org(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/")

    @task
    def get_newsfeed(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/newsfeed/")

    @task
    def get_people_group_by_id(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/people-group/{GROUP_TO_TEST}/")

    @task
    def get_people_group_member(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/people-group/{GROUP_TO_TEST}/member?limit=30")

    @task
    def get_people_group_project(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/people-group/{GROUP_TO_TEST}/project/")

    @task
    def get_recommended_project_user(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/recommended-project/user/")

    @task
    def get_recommended_project_user_random(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/recommended-project/user/random/")

    @task
    def get_recommended_user_user(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/recommended-user/user/")

    @task
    def get_recommended_user_user_random(self):
        self.client.get(f"/v1/organization/{ORGANIZATION_CODE}/recommended-user/user/random/")

    @task
    def get_project_by_id(self):
        self.client.get(f"/v1/project/{PROJECT_TO_TEST}/")

    @task
    def search(self):
        self.client.get(f"/v1/search/{SEARCH_TERM}/")

    @task
    def search_people_group(self):
        self.client.get(f"/v1/search/{SEARCH_TERM}/?types=people_group")

    @task
    def search_user(self):
        self.client.get(f"/v1/search/{SEARCH_TERM}/?types=user")

    @task
    def search_project(self):
        self.client.get(f"/v1/search/{SEARCH_TERM}/?types=project")

    @task
    def get_user_by_id(self):
        self.client.get(f"/v1/user/{USER_ID}/")
