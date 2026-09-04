from types import SimpleNamespace
from unittest.mock import _Call, call

# from azure.ai.translation.text.models import TranslateInputItem, TranslationTarget
from apps.commons.test import JwtAPITestCase


class MockTranslateTestCase(JwtAPITestCase):
    @classmethod
    def translator_side_effect(cls, body: list[TranslateInputItem]) -> list[dict]:
        """
        This side effect is meant to be used with unittest mock. It will mock every call
        made to the Azure translator API.

        Arguments
        ---------
        - body (list of TranslateInputItem): The translation request, as built by
          `AzureTranslatorService.translate_text_content`.

        Returns
        -------
        - A list of SimpleNamespace objects that simulates the Azure translator API response.
        """
        input_item = body[0]
        return [
            SimpleNamespace(
                detected_language=SimpleNamespace(language="en", score=1.0),
                translations=[
                    SimpleNamespace(
                        text=f"{target.language} : {input_item.text}",
                        language=target.language,
                    )
                    for target in input_item.targets
                ],
            )
        ]

    @classmethod
    def translate_call(cls, text: str, languages, text_type: str = "plain") -> _Call:
        """
        Builds the `unittest.mock.call` expected from a `TextTranslationClient.translate`
        invocation, for use with `assert_has_calls`.
        """
        return call(
            body=[
                TranslateInputItem(
                    text=text,
                    text_type=text_type,
                    targets=[TranslationTarget(language=lang) for lang in languages],
                )
            ],
        )
