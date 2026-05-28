from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENAI_MODEL = "gpt-5.1"


class GroqPlanner:
    def __init__(self) -> None:
        load_dotenv()
        _enable_system_cert_store()
        self.groq_model = os.getenv("AXIOM_GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.openai_model = os.getenv("AXIOM_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.api_keys = [
            value
            for value in (
                os.getenv("GROQ_API_KEY"),
                os.getenv("groq_api_key_1"),
                os.getenv("groq_api_key_2"),
            )
            if value
        ]
        self.provider_name = "openai" if self.openai_api_key else "groq"

    def available(self) -> bool:
        return bool(self.openai_api_key or self.api_keys)

    def create_plan(
        self,
        manifesto: dict[str, Any],
        title: str,
        deterministic_questions: list[str],
        deterministic_visualizations: list[dict[str, Any]],
        derived_measures: list[dict[str, Any]],
        brand_guideline: str = "",
        visual_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if not self.available():
            return None

        if self.openai_api_key:
            try:
                return self._request_openai_plan(
                    manifesto=manifesto,
                    title=title,
                    deterministic_questions=deterministic_questions,
                    deterministic_visualizations=deterministic_visualizations,
                    derived_measures=derived_measures,
                    brand_guideline=brand_guideline,
                    visual_history=visual_history or [],
                )
            except Exception:
                pass

        for api_key in self.api_keys:
            try:
                return self._request_plan(
                    api_key=api_key,
                    manifesto=manifesto,
                    title=title,
                    deterministic_questions=deterministic_questions,
                    deterministic_visualizations=deterministic_visualizations,
                    derived_measures=derived_measures,
                    brand_guideline=brand_guideline,
                    visual_history=visual_history or [],
                )
            except Exception:
                continue

        return None

    def _request_openai_plan(
        self,
        manifesto: dict[str, Any],
        title: str,
        deterministic_questions: list[str],
        deterministic_visualizations: list[dict[str, Any]],
        derived_measures: list[dict[str, Any]],
        brand_guideline: str,
        visual_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        parsed = self._request_openai_json(
            system_prompt=(
                "You are AXIOM's analysis planner. Create concise, professional, "
                "enterprise-grade BI analysis plans. Return only valid JSON."
            ),
            payload=_plan_payload(
                manifesto=manifesto,
                title=title,
                deterministic_questions=deterministic_questions,
                deterministic_visualizations=deterministic_visualizations,
                derived_measures=derived_measures,
                brand_guideline=brand_guideline,
                visual_history=visual_history,
            ),
            max_completion_tokens=2200,
            temperature=0.2,
        )
        return _normalize_plan_response(parsed)

    def _request_plan(
        self,
        api_key: str,
        manifesto: dict[str, Any],
        title: str,
        deterministic_questions: list[str],
        deterministic_visualizations: list[dict[str, Any]],
        derived_measures: list[dict[str, Any]],
        brand_guideline: str,
        visual_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=self.groq_model,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=2200,
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
                        _plan_payload(
                            manifesto=manifesto,
                            title=title,
                            deterministic_questions=deterministic_questions,
                            deterministic_visualizations=deterministic_visualizations,
                            derived_measures=derived_measures,
                            brand_guideline=brand_guideline,
                            visual_history=visual_history,
                        ),
                        default=str,
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or "{}"
        return _normalize_plan_response(json.loads(content))

    def create_document_blueprint(
        self,
        title: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
        brand_guideline: str = "",
    ) -> dict[str, Any] | None:
        if not self.available():
            return None

        if self.openai_api_key:
            try:
                return self._request_openai_document_blueprint(title, manifesto, analysis_plan, brand_guideline)
            except Exception:
                pass

        for api_key in self.api_keys:
            try:
                return self._request_document_blueprint(api_key, title, manifesto, analysis_plan, brand_guideline)
            except Exception:
                continue
        return None

    def _request_openai_document_blueprint(
        self,
        title: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
        brand_guideline: str,
    ) -> dict[str, Any] | None:
        parsed = self._request_openai_json(
            system_prompt=(
                "You are AXIOM's document architect. Return only valid JSON. "
                "Create a varied report/deck structure suited to the dataset, not a generic template."
            ),
            payload=_document_blueprint_payload(title, manifesto, analysis_plan, brand_guideline),
            max_completion_tokens=1600,
            temperature=0.35,
        )
        blueprint = parsed.get("document_blueprint")
        return blueprint if isinstance(blueprint, dict) else None

    def _request_document_blueprint(
        self,
        api_key: str,
        title: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
        brand_guideline: str,
    ) -> dict[str, Any] | None:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=self.groq_model,
            response_format={"type": "json_object"},
            temperature=0.35,
            max_completion_tokens=1600,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AXIOM's document architect. Return only valid JSON. "
                        "Create a varied report/deck structure suited to the dataset, not a generic template."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        _document_blueprint_payload(title, manifesto, analysis_plan, brand_guideline),
                        default=str,
                    ),
                },
            ],
        )
        parsed = json.loads(completion.choices[0].message.content or "{}")
        blueprint = parsed.get("document_blueprint")
        return blueprint if isinstance(blueprint, dict) else None

    def repair_code(
        self,
        broken_code: str,
        error_text: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> str | None:
        if not self.available():
            return None

        if self.openai_api_key:
            try:
                return self._request_openai_code_repair(broken_code, error_text, manifesto, analysis_plan)
            except Exception:
                pass

        for api_key in self.api_keys:
            try:
                return self._request_code_repair(api_key, broken_code, error_text, manifesto, analysis_plan)
            except Exception:
                continue

        return None

    def _request_code_repair(
        self,
        api_key: str,
        broken_code: str,
        error_text: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> str | None:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=self.groq_model,
            temperature=0.1,
            max_completion_tokens=2400,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You repair only temporary AXIOM analyst scripts. Return raw Python code only. "
                        "Do not edit package files, do not use networking, and do not access files outside "
                        "the current working directory. The script must read analysis_input.csv, manifesto.json, "
                        "and analysis_plan.json, then write result.json."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "broken_code": broken_code,
                            "error_text": error_text[-6000:],
                            "data_manifesto": manifesto,
                            "analysis_plan": analysis_plan,
                        },
                        default=str,
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or ""
        return _strip_code_fence(content)

    def _request_openai_code_repair(
        self,
        broken_code: str,
        error_text: str,
        manifesto: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> str | None:
        content = self._request_openai_text(
            system_prompt=(
                "You repair only temporary AXIOM analyst scripts. Return raw Python code only. "
                "Do not edit package files, do not use networking, and do not access files outside "
                "the current working directory. The script must read analysis_input.csv, manifesto.json, "
                "and analysis_plan.json, then write result.json."
            ),
            payload={
                "broken_code": broken_code,
                "error_text": error_text[-6000:],
                "data_manifesto": manifesto,
                "analysis_plan": analysis_plan,
            },
            max_completion_tokens=2400,
            temperature=0.1,
        )
        return _strip_code_fence(content)

    def _request_openai_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        max_completion_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        content = self._request_openai_text(
            system_prompt=system_prompt,
            payload=payload,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(content or "{}")

    def _request_openai_text(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        max_completion_tokens: int,
        temperature: float,
        response_format: dict[str, str] | None = None,
    ) -> str:
        if not self.openai_api_key:
            return ""
        client = OpenAI(api_key=self.openai_api_key)
        kwargs: dict[str, Any] = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
            "max_completion_tokens": max_completion_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if self.openai_model.startswith("gpt-5"):
            kwargs["reasoning_effort"] = os.getenv("AXIOM_OPENAI_REASONING_EFFORT", "none")
        else:
            kwargs["temperature"] = temperature

        completion = client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content or ""


def _plan_payload(
    manifesto: dict[str, Any],
    title: str,
    deterministic_questions: list[str],
    deterministic_visualizations: list[dict[str, Any]],
    derived_measures: list[dict[str, Any]],
    brand_guideline: str,
    visual_history: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "task": "Create an analysis plan for this dataset.",
        "title": title,
        "data_manifesto": manifesto,
        "baseline_questions": deterministic_questions,
        "available_derived_measures": derived_measures,
        "baseline_visualizations": deterministic_visualizations,
        "recent_visual_history": visual_history,
        "visual_diversity_policy": {
            "goal": "Avoid repeating the same chart signatures from recent reruns. Prefer a coherent story arc.",
            "angles_to_consider": [
                "cohort",
                "funnel",
                "revenue_growth",
                "customer_behavior",
                "product_mix",
                "inventory_health",
                "review_quality",
                "payment_behavior",
                "geography",
                "relationship_diagnostics",
            ],
            "required": (
                "Recommend charts that tell a sequence: context, driver, comparison, behavior, "
                "risk/opportunity. Express cohort, funnel, category mix, review/rating, inventory, "
                "geography, and customer behavior views using the supported chart types."
            ),
        },
        "brand_guideline_excerpt": brand_guideline[:5000],
        "required_json_shape": {
            "recommended_questions": ["string"],
            "data_quality_focus": ["string"],
            "business_context_assumptions": ["string"],
            "recommended_visualizations": [
                {
                    "chart_type": "bar | line | scatter | histogram | heatmap",
                    "title": "string",
                    "x": "column name",
                    "y": "column name",
                    "columns": ["column names for heatmap"],
                    "aggregation": "sum | mean | count | none | correlation",
                    "story_role": "context | trend | driver | segment_compare | behavior | risk | opportunity | distribution",
                    "angle": "cohort | funnel | revenue_growth | customer_behavior | product_mix | inventory_health | review_quality | payment_behavior | geography | relationship_diagnostics",
                    "rationale": "string",
                }
            ],
            "additional_measures_to_create": [
                {
                    "name": "string",
                    "formula": "formula using available columns",
                    "description": "string",
                }
            ],
            "planned_outputs": ["string"],
            "document_blueprint": {
                "style": "executive_technical | board_brief | diagnostic_deep_dive | operations_review",
                "report_sections": [
                    {
                        "type": "executive_summary | kpi_summary | chart_story | data_model | data_quality | methodology | self_healing",
                        "title": "string",
                        "intent": "string",
                        "chart_refs": [0],
                    }
                ],
                "deck_slides": [
                    {
                        "type": "title | executive_summary | kpi | chart | data_model | data_quality | self_healing",
                        "title": "string",
                        "chart_ref": 0,
                    }
                ],
                "theme": {
                    "name": "string",
                    "background": "brand-compatible hex color",
                    "surface": "brand-compatible hex color",
                    "text": "brand-compatible hex color",
                    "accent": "brand-compatible hex color",
                    "secondary_accent": "brand-compatible hex color",
                    "chart_palette": ["brand-compatible hex colors"],
                },
            },
        },
    }


def _document_blueprint_payload(
    title: str,
    manifesto: dict[str, Any],
    analysis_plan: dict[str, Any],
    brand_guideline: str,
) -> dict[str, Any]:
    return {
        "title": title,
        "dataset_summary": {
            "source": manifesto.get("source"),
            "row_count": manifesto.get("row_count"),
            "analysis_row_count": manifesto.get("analysis_row_count"),
            "relationships": manifesto.get("relationships", [])[:8],
            "derived_measures": manifesto.get("derived_measures", [])[:8],
            "warnings": manifesto.get("anomaly_warnings", [])[:8],
        },
        "recommended_questions": analysis_plan.get("recommended_questions", [])[:10],
        "recommended_visualizations": analysis_plan.get("recommended_visualizations", [])[:8],
        "brand_guideline_excerpt": brand_guideline[:3000],
        "theme_instruction": (
            "Use AXIOM brand colors creatively. Prefer a lighter executive PowerPoint "
            "background unless the requested style clearly needs dark mode."
        ),
        "allowed_report_section_types": [
            "executive_summary",
            "kpi_summary",
            "chart_story",
            "data_model",
            "data_quality",
            "methodology",
            "self_healing",
        ],
        "allowed_slide_types": [
            "title",
            "executive_summary",
            "kpi",
            "chart",
            "data_model",
            "data_quality",
            "self_healing",
        ],
        "required_json_shape": {
            "document_blueprint": {
                "style": "board_brief | diagnostic_deep_dive | operations_review | executive_technical",
                "report_sections": [
                    {
                        "type": "allowed report section type",
                        "title": "string",
                        "intent": "string",
                        "chart_refs": [0],
                    }
                ],
                "deck_slides": [
                    {
                        "type": "allowed slide type",
                        "title": "string",
                        "chart_ref": 0,
                    }
                ],
                "theme": {
                    "name": "string",
                    "background": "hex",
                    "surface": "hex",
                    "text": "hex",
                    "accent": "hex",
                    "secondary_accent": "hex",
                    "chart_palette": ["hex"],
                },
            }
        },
    }


def _normalize_plan_response(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommended_questions": _string_list(parsed.get("recommended_questions")),
        "data_quality_focus": _string_list(parsed.get("data_quality_focus")),
        "business_context_assumptions": _string_list(parsed.get("business_context_assumptions")),
        "recommended_visualizations": _dict_list(parsed.get("recommended_visualizations")),
        "additional_measures_to_create": _dict_list(parsed.get("additional_measures_to_create")),
        "planned_outputs": _string_list(parsed.get("planned_outputs")),
        "document_blueprint": parsed.get("document_blueprint") if isinstance(parsed.get("document_blueprint"), dict) else {},
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped
