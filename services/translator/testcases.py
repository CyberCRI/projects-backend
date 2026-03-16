from types import SimpleNamespace

from apps.commons.test import JwtAPITestCase


class MockTranslateTestCase(JwtAPITestCase):
    @classmethod
    def translator_side_effect(
        cls, body: list[str], to_language: list[str], text_type: str = "plain"
    ) -> list[dict]:
        """
        This side effect is meant to be used with unittest mock. It will mock every call
        made to the Azure translator API.

        Arguments
        ---------
        - content (str): The text content to be translated.
        - languages (list of str): The target languages for translation.

        Returns
        -------
        - A list of SimpleNamespace objects that simulates the Azure translator API response.
        """

        return [
            SimpleNamespace(
                detected_language=SimpleNamespace(language="en", score=1.0),
                translations=[
                    SimpleNamespace(text=f"{lang} : {body[0]}", to=lang)
                    for lang in to_language
                ],
            )
        ]
