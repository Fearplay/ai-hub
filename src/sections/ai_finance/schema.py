"""JSON Schemas for AI Finance structured outputs.

Every schema here is consumed by :mod:`src.services.ai_provider` so the
model is forced into structured-output mode. Keep schemas tight - extra
optional fields mean extra tokens on every response, and the right-hand
visualisations only render the fields they know about anyway.
"""

from __future__ import annotations


BUDGET_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "currency",
        "income",
        "method",
        "splits",
        "breakdown",
        "warnings",
        "suggestions",
        "summary",
    ],
    "properties": {
        "currency": {"type": "string"},
        "income": {"type": "number"},
        "method": {
            "type": "string",
            "enum": [
                "50_30_20",
                "60_20_20",
                "70_20_10",
                "zero_based",
                "custom",
            ],
        },
        "splits": {
            "type": "object",
            "additionalProperties": False,
            "required": ["needs", "wants", "saving"],
            "properties": {
                "needs": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["percent", "amount", "label"],
                    "properties": {
                        "percent": {"type": "number"},
                        "amount": {"type": "number"},
                        "label": {"type": "string"},
                    },
                },
                "wants": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["percent", "amount", "label"],
                    "properties": {
                        "percent": {"type": "number"},
                        "amount": {"type": "number"},
                        "label": {"type": "string"},
                    },
                },
                "saving": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["percent", "amount", "label"],
                    "properties": {
                        "percent": {"type": "number"},
                        "amount": {"type": "number"},
                        "label": {"type": "string"},
                    },
                },
            },
        },
        "breakdown": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "category",
                    "group",
                    "percent",
                    "amount",
                    "note",
                ],
                "properties": {
                    "category": {"type": "string"},
                    "group": {
                        "type": "string",
                        "enum": ["needs", "wants", "saving"],
                    },
                    "percent": {"type": "number"},
                    "amount": {"type": "number"},
                    "note": {"type": "string"},
                },
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
    },
}


SAVINGS_PLAN_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "currency",
        "goal_amount",
        "current_savings",
        "monthly_contribution",
        "months_to_goal",
        "percent_of_income",
        "milestones",
        "tips",
        "summary",
    ],
    "properties": {
        "currency": {"type": "string"},
        "goal_amount": {"type": "number"},
        "current_savings": {"type": "number"},
        "monthly_contribution": {"type": "number"},
        "months_to_goal": {"type": "number"},
        "percent_of_income": {"type": "number"},
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "amount", "after_months"],
                "properties": {
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                    "after_months": {"type": "number"},
                },
            },
        },
        "tips": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
    },
}


INVESTMENT_SCENARIO_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "currency",
        "amount",
        "horizon_years",
        "scenarios",
        "diversification_note",
        "risk_note",
        "disclaimer",
    ],
    "properties": {
        "currency": {"type": "string"},
        "amount": {"type": "number"},
        "horizon_years": {"type": "number"},
        "scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "risk_level",
                    "expected_annual_return_pct",
                    "projected_value",
                    "allocation",
                    "description",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "risk_level": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "growth"],
                    },
                    "expected_annual_return_pct": {"type": "number"},
                    "projected_value": {"type": "number"},
                    "allocation": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["asset_class", "percent"],
                            "properties": {
                                "asset_class": {"type": "string"},
                                "percent": {"type": "number"},
                            },
                        },
                    },
                    "description": {"type": "string"},
                },
            },
        },
        "diversification_note": {"type": "string"},
        "risk_note": {"type": "string"},
        "disclaimer": {"type": "string"},
    },
}


EXPENSE_ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "currency",
        "period",
        "total_income",
        "total_expenses",
        "net_cash_flow",
        "categories",
        "top_outflows",
        "recurring",
        "suggestions",
        "summary",
    ],
    "properties": {
        "currency": {"type": "string"},
        "period": {"type": "string"},
        "total_income": {"type": "number"},
        "total_expenses": {"type": "number"},
        "net_cash_flow": {"type": "number"},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "amount", "percent_of_expenses"],
                "properties": {
                    "name": {"type": "string"},
                    "amount": {"type": "number"},
                    "percent_of_expenses": {"type": "number"},
                },
            },
        },
        "top_outflows": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "amount", "note"],
                "properties": {
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                    "note": {"type": "string"},
                },
            },
        },
        "recurring": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "monthly_amount", "category"],
                "properties": {
                    "label": {"type": "string"},
                    "monthly_amount": {"type": "number"},
                    "category": {"type": "string"},
                },
            },
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
    },
}


TAX_CHECKLIST_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "country",
        "filing_status",
        "year",
        "checklist",
        "deadlines",
        "documents_needed",
        "tips",
        "disclaimer",
    ],
    "properties": {
        "country": {"type": "string"},
        "filing_status": {"type": "string"},
        "year": {"type": "string"},
        "checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail"],
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        },
        "deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "date_or_window"],
                "properties": {
                    "label": {"type": "string"},
                    "date_or_window": {"type": "string"},
                },
            },
        },
        "documents_needed": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tips": {
            "type": "array",
            "items": {"type": "string"},
        },
        "disclaimer": {"type": "string"},
    },
}


TIP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "body", "next_step", "category"],
    "properties": {
        "title": {"type": "string"},
        "body": {"type": "string"},
        "next_step": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "budget",
                "savings",
                "investing",
                "expenses",
                "taxes",
                "insurance",
                "general",
            ],
        },
    },
}


INSURANCE_REVIEW_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "household",
        "policies",
        "coverage_gaps",
        "duplicates",
        "watch_outs",
        "suggestions",
        "summary",
        "disclaimer",
    ],
    "properties": {
        "household": {"type": "string"},
        "policies": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "kind", "limit_note", "premium_note"],
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"type": "string"},
                    "limit_note": {"type": "string"},
                    "premium_note": {"type": "string"},
                },
            },
        },
        "coverage_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["topic", "risk", "severity"],
                "properties": {
                    "topic": {"type": "string"},
                    "risk": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
            },
        },
        "duplicates": {
            "type": "array",
            "items": {"type": "string"},
        },
        "watch_outs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
        "disclaimer": {"type": "string"},
    },
}
