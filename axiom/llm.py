from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqPlanner:
    def __init__(self) -> None:
        load_dotenv()
        self.model = os.getenv("AXIOM_GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.api_keys = [
            value
            for value in (
                os.getenv("GROQ_API_KEY"),
                os.getenv("groq_api_key_1"),
                os.getenv("groq_api_key_2"),
            )
            if value
        ]

    def available(self) -> bool:
        return bool(self.api_keys)

    def create_plan(
        self,
        manifesto: dict[str, Any],
        title: str,
        deterministic_questions: list[str],
        brand_guideline: str = "",
    ) -> dict[str, Any] | None:
        if not self.available():
            return None

        for api_key in self.api_keys:
            try:
                return self._request_plan(
                    api_key=api_key,
                    manifesto=manifesto,
                    title=title,
                    deterministic_questions=deterministic_questions,
                    brand_guideline=brand_guideline,
                )
            except Exception:
                continue

        return None

    def _request_plan(
        self,
        api_key: str,
        manifesto: dict[str, Any],
        title: str,
        deterministic_questions: list[str],
        brand_guideline: str,
    ) -> dict[str, Any]:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=1200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AXIOM's analysis planner. Create concise, professional, "
                        "enterprise-grade BI analysis plans. Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Create an analysis plan for this dataset.",
                            "title": title,
                            "data_manifesto": manifesto,
                            "baseline_questions": deterministic_questions,
                            "brand_guideline_excerpt": brand_guideline[:5000],
                            "required_json_shape": {
                                "recommended_questions": ["string"],
                                "data_quality_focus": ["string"],
                                "business_context_assumptions": ["string"],
                                "planned_outputs": ["string"],
                            },
                        },
                        default=str,
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return {
            "recommended_questions": _string_list(parsed.get("recommended_questions")),
            "data_quality_focus": _string_list(parsed.get("data_quality_focus")),
            "business_context_assumptions": _string_list(parsed.get("business_context_assumptions")),
            "planned_outputs": _string_list(parsed.get("planned_outputs")),
        }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

