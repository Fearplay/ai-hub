"""Orchestration for AI Finance.

Every interactive call from the tabs / chat lands here. The pipeline is
deliberately thin: each public function

1. validates inputs,
2. forwards to :func:`src.services.ai_provider.run` with a schema +
   compact prompt,
3. caches the result on :data:`STATE`,
4. logs start / done / failed events,
5. asks the right-hand panel (and where needed the full section view)
   to refresh through :data:`REFS`.

No section ever imports openai / anthropic directly - the provider call
is centralised so cost-tracking, hallucination policy and the web-search
toggle are honoured in one place.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from src.services import ai_provider, exporter, store
from src.services import logger as logger_service
from src.services import settings_store
from src.services.cost_tracker import COST
from src.sections.ai_finance import data as finance_data
from src.sections.ai_finance import prompts, schema
from src.sections.ai_finance.refs import REFS
from src.sections.ai_finance.state import (
    STATE,
    FinanceChatMessage,
)
from src.sections.ai_finance.strings import s


# -- Public types -----------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""


# -- helpers ----------------------------------------------------------


def _now_str() -> str:
    return datetime.now().strftime("%H:%M")


def _request_full_refresh() -> None:
    """Re-run ``build_view`` on the GUI thread.

    Used after a structured pipeline step finishes - the tab swap +
    new visuals only show up when we tear down the old tree.
    """
    try:
        from src.app import request_section_refresh

        request_section_refresh()
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", "request_full_refresh_failed", exc
        )


def _set_activity(value: str) -> None:
    prev = STATE.activity
    STATE.activity = value
    if prev != value:
        logger_service.log_event(
            "INFO",
            "ai_finance.pipeline",
            "activity_change",
            prev=prev,
            new=value,
        )
    REFS.request_context_refresh()


def _set_error(stage: str, message: str) -> PipelineResult:
    STATE.activity = "error"
    STATE.last_error = message
    REFS.request_context_refresh()
    logger_service.log_event(
        "ERROR", "ai_finance.pipeline", f"{stage}_error", message=message
    )
    return PipelineResult(ok=False, error=message)


def _clean_text(text: str) -> str:
    return (text or "").replace("\u2014", "-").replace("\u2013", "-")


def _clean_json(payload: Any) -> Any:
    if isinstance(payload, str):
        return _clean_text(payload)
    if isinstance(payload, list):
        return [_clean_json(item) for item in payload]
    if isinstance(payload, dict):
        return {k: _clean_json(v) for k, v in payload.items()}
    return payload


def _resolve_lang(output_lang: str) -> str:
    code = (output_lang or "en").strip().lower()
    return code if code in {"en", "cs"} else "en"


def _provider_call(
    *,
    stage: str,
    system: str,
    user: str,
    schema_dict: Optional[dict],
    schema_name: str,
    max_output_tokens: int,
    enable_web_search: bool = False,
    output_lang: str,
) -> ai_provider.ProviderResult:
    logger_service.log_event(
        "INFO",
        "ai_finance.pipeline",
        f"{stage}_start",
        output_lang=output_lang,
        web_search=enable_web_search,
        chars=len(user),
    )
    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=schema_dict,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
            enable_web_search=enable_web_search,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", f"{stage}_provider_error", exc
        )
        raise
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", f"{stage}_unexpected_error", exc
        )
        raise
    try:
        COST.add(result.provider, result.model, result.tokens_in, result.tokens_out)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", f"{stage}_cost_failed", exc
        )
    logger_service.log_event(
        "INFO",
        "ai_finance.pipeline",
        f"{stage}_done",
        provider=result.provider,
        model=result.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
    )
    return result


# -- Budget -----------------------------------------------------------


def create_budget(
    *,
    output_lang: str,
    currency: str,
    income: float,
    method: str,
    savings_goal: str,
    essentials: str,
    lifestyle: str,
    notes: str = "",
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_budget_input = {
        "currency": currency,
        "income": income,
        "method": method,
        "savings_goal": savings_goal,
        "essentials": essentials,
        "lifestyle": lifestyle,
        "notes": notes,
    }

    if income <= 0 or not (essentials.strip() or lifestyle.strip() or savings_goal.strip()):
        return _set_error(
            "create_budget",
            s(output_lang)["error_no_input"],
        )

    _set_activity("generating")
    try:
        result = _provider_call(
            stage="create_budget",
            system=prompts.BUDGET_CREATE_SYSTEM,
            user=prompts.build_budget_user(
                output_lang=output_lang,
                currency=currency,
                income=income,
                method=method,
                savings_goal=savings_goal,
                essentials=essentials,
                lifestyle=lifestyle,
                notes=notes,
            ),
            schema_dict=schema.BUDGET_SCHEMA,
            schema_name="BudgetPlan",
            max_output_tokens=1600,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "create_budget",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )

    if not result.data:
        return _set_error("create_budget", "Provider returned an empty payload.")

    STATE.budget = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def edit_budget(
    *,
    output_lang: str,
    instructions: list[str],
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    if STATE.budget is None:
        return _set_error("edit_budget", "Build a budget before editing it.")

    _set_activity("generating")
    try:
        result = _provider_call(
            stage="edit_budget",
            system=prompts.BUDGET_EDIT_SYSTEM,
            user=prompts.build_budget_edit_user(
                output_lang=output_lang,
                current_budget=STATE.budget,
                instructions=instructions,
            ),
            schema_dict=schema.BUDGET_SCHEMA,
            schema_name="BudgetPlan",
            max_output_tokens=1600,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "edit_budget",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )

    if not result.data:
        return _set_error("edit_budget", "Provider returned an empty payload.")
    STATE.budget = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Savings ----------------------------------------------------------


def generate_savings_plan(
    *,
    output_lang: str,
    currency: str,
    income: float,
    current_savings: float,
    goal_amount: float,
    goal_label: str,
    target_months: int,
    notes: str = "",
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_savings_input = {
        "currency": currency,
        "income": income,
        "current_savings": current_savings,
        "goal_amount": goal_amount,
        "goal_label": goal_label,
        "target_months": target_months,
        "notes": notes,
    }

    if goal_amount <= 0 or target_months <= 0:
        return _set_error(
            "generate_savings_plan", s(output_lang)["error_no_input"]
        )

    _set_activity("generating")
    try:
        result = _provider_call(
            stage="generate_savings_plan",
            system=prompts.SAVINGS_PLAN_SYSTEM,
            user=prompts.build_savings_plan_user(
                output_lang=output_lang,
                currency=currency,
                income=income,
                current_savings=current_savings,
                goal_amount=goal_amount,
                goal_label=goal_label,
                target_months=target_months,
                notes=notes,
            ),
            schema_dict=schema.SAVINGS_PLAN_SCHEMA,
            schema_name="SavingsPlan",
            max_output_tokens=1200,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "generate_savings_plan",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )
    if not result.data:
        return _set_error(
            "generate_savings_plan", "Provider returned an empty payload."
        )
    STATE.savings_plan = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Investment scenarios ---------------------------------------------


def generate_investment_scenarios(
    *,
    output_lang: str,
    currency: str,
    amount: float,
    horizon_years: int,
    risk: str,
    focus: str,
    notes: str = "",
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_invest_input = {
        "currency": currency,
        "amount": amount,
        "horizon_years": horizon_years,
        "risk": risk,
        "focus": focus,
        "notes": notes,
    }
    if amount <= 0 or horizon_years <= 0:
        return _set_error(
            "generate_investment_scenarios", s(output_lang)["error_no_input"]
        )

    _set_activity("generating")
    try:
        result = _provider_call(
            stage="generate_investment_scenarios",
            system=prompts.INVESTMENT_SCENARIO_SYSTEM,
            user=prompts.build_investment_user(
                output_lang=output_lang,
                currency=currency,
                amount=amount,
                horizon_years=horizon_years,
                risk=risk,
                focus=focus,
                notes=notes,
            ),
            schema_dict=schema.INVESTMENT_SCENARIO_SCHEMA,
            schema_name="InvestmentScenario",
            max_output_tokens=1500,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "generate_investment_scenarios",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )
    if not result.data:
        return _set_error(
            "generate_investment_scenarios",
            "Provider returned an empty payload.",
        )
    STATE.investment_scenario = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Expense analysis -------------------------------------------------


def analyze_expenses(
    *,
    output_lang: str,
    currency: str,
    period: str,
    focus: str,
    goal: str,
    statement_text: str,
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_analysis_input = {
        "currency": currency,
        "period": period,
        "focus": focus,
        "goal": goal,
        "has_upload": bool(statement_text.strip()),
    }
    if not (statement_text.strip() or focus.strip() or goal.strip()):
        return _set_error(
            "analyze_expenses", s(output_lang)["error_no_input"]
        )

    _set_activity("analyzing")
    try:
        result = _provider_call(
            stage="analyze_expenses",
            system=prompts.EXPENSE_ANALYSIS_SYSTEM,
            user=prompts.build_expense_analysis_user(
                output_lang=output_lang,
                currency=currency,
                period=period,
                focus=focus,
                goal=goal,
                statement_text=statement_text,
            ),
            schema_dict=schema.EXPENSE_ANALYSIS_SCHEMA,
            schema_name="ExpenseAnalysis",
            max_output_tokens=2000,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "analyze_expenses",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )
    if not result.data:
        return _set_error("analyze_expenses", "Provider returned an empty payload.")
    STATE.expense_analysis = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Tax checklist ----------------------------------------------------


def generate_tax_checklist(
    *,
    output_lang: str,
    country: str,
    filing_status: str,
    year: str,
    notes: str,
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_tax_input = {
        "country": country,
        "filing_status": filing_status,
        "year": year,
        "notes": notes,
    }
    if not (country.strip() or filing_status.strip() or notes.strip()):
        return _set_error("generate_tax_checklist", s(output_lang)["error_no_input"])

    _set_activity("generating")
    try:
        result = _provider_call(
            stage="generate_tax_checklist",
            system=prompts.TAX_CHECKLIST_SYSTEM,
            user=prompts.build_tax_user(
                output_lang=output_lang,
                country=country,
                filing_status=filing_status,
                year=year,
                notes=notes,
            ),
            schema_dict=schema.TAX_CHECKLIST_SCHEMA,
            schema_name="TaxChecklist",
            max_output_tokens=1500,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "generate_tax_checklist",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )
    if not result.data:
        return _set_error(
            "generate_tax_checklist", "Provider returned an empty payload."
        )
    STATE.tax_checklist = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Insurance review -------------------------------------------------


def review_insurance(
    *,
    output_lang: str,
    household: str,
    assets: str,
    existing: str,
    concerns: str,
    document_text: str,
) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    STATE.last_insurance_input = {
        "household": household,
        "assets": assets,
        "existing": existing,
        "concerns": concerns,
        "has_upload": bool(document_text.strip()),
    }
    if not (existing.strip() or document_text.strip()):
        return _set_error("review_insurance", s(output_lang)["error_no_input"])

    _set_activity("analyzing")
    try:
        result = _provider_call(
            stage="review_insurance",
            system=prompts.INSURANCE_REVIEW_SYSTEM,
            user=prompts.build_insurance_user(
                output_lang=output_lang,
                household=household,
                assets=assets,
                existing=existing,
                concerns=concerns,
                document_text=document_text,
            ),
            schema_dict=schema.INSURANCE_REVIEW_SCHEMA,
            schema_name="InsuranceReview",
            max_output_tokens=1800,
            output_lang=output_lang,
        )
    except Exception as exc:
        return _set_error(
            "review_insurance",
            s(output_lang)["error_provider"].format(error=str(exc)),
        )
    if not result.data:
        return _set_error("review_insurance", "Provider returned an empty payload.")
    STATE.insurance_review = _clean_json(result.data)
    STATE.activity = "ready"
    REFS.request_context_refresh()
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Chat -------------------------------------------------------------


def append_chat_user(text: str, *, attachment_name: str = "") -> None:
    STATE.chat_messages.append(
        FinanceChatMessage(
            role="user",
            text=text,
            time=_now_str(),
            attachment_name=attachment_name,
        )
    )


def append_chat_assistant(text: str) -> None:
    STATE.chat_messages.append(
        FinanceChatMessage(role="assistant", text=text, time=_now_str())
    )


def send_chat_message(*, output_lang: str, user_text: str) -> PipelineResult:
    output_lang = _resolve_lang(output_lang)
    user_text = (user_text or "").strip()
    if not user_text:
        return PipelineResult(ok=False, error="Empty message.")

    append_chat_user(user_text)

    STATE.chat_running = True
    REFS.dispatch(_request_full_refresh)

    history = [
        {"role": m.role, "text": m.text}
        for m in STATE.chat_messages[:-1]
        if m.text
    ]

    structured_context: dict[str, Any] = {
        "budget": STATE.budget,
        "savings_plan": STATE.savings_plan,
        "expense_analysis": STATE.expense_analysis,
        "investment_scenario": STATE.investment_scenario,
        "tax_checklist": STATE.tax_checklist,
        "insurance_review": STATE.insurance_review,
    }

    enable_web = settings_store.get_web_search_enabled()
    _set_activity("thinking")
    try:
        result = _provider_call(
            stage="send_chat_message",
            system=prompts.CHAT_MODE_SYSTEM,
            user=prompts.build_chat_user_block(
                output_lang=output_lang,
                history=history,
                attachments=STATE.chat_attachments,
                structured_context=structured_context,
                user_text=user_text,
            ),
            schema_dict=None,
            schema_name="chat",
            max_output_tokens=900,
            enable_web_search=enable_web,
            output_lang=output_lang,
        )
    except Exception as exc:
        STATE.chat_running = False
        append_chat_assistant(
            s(output_lang)["error_provider"].format(error=str(exc))
        )
        STATE.activity = "error"
        REFS.dispatch(_request_full_refresh)
        return PipelineResult(ok=False, error=str(exc))

    reply = _clean_text(result.text)
    if not reply.strip():
        reply = "(empty response)"
    append_chat_assistant(reply)
    STATE.chat_running = False
    STATE.activity = "ready"
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# -- Save full analysis ----------------------------------------------


def _markdown_for_budget(budget: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['nav_label']} - {txt['budget_summary_title']}"]
    lines.append("")
    summary = budget.get("summary") or ""
    if summary:
        lines.append(summary)
        lines.append("")
    currency = budget.get("currency") or ""
    income = budget.get("income") or 0
    lines.append(f"**{txt['form_currency']}**: {currency}")
    lines.append(f"**Income**: {income} {currency}")
    method = budget.get("method") or ""
    lines.append(f"**{txt['budget_method_label']}**: {method}")
    lines.append("")
    splits = budget.get("splits") or {}
    for group_key in ("needs", "wants", "saving"):
        group = splits.get(group_key) or {}
        label = group.get("label") or group_key.title()
        percent = group.get("percent") or 0
        amount = group.get("amount") or 0
        lines.append(f"- **{label}**: {percent}% ({amount} {currency})")
    lines.append("")
    lines.append(f"## {txt['breakdown_title']}")
    for row in budget.get("breakdown") or []:
        category = row.get("category") or ""
        percent = row.get("percent") or 0
        amount = row.get("amount") or 0
        note = row.get("note") or ""
        if note:
            lines.append(f"- {category} - {percent}% / {amount} {currency} - {note}")
        else:
            lines.append(f"- {category} - {percent}% / {amount} {currency}")
    warnings = budget.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append(f"## {txt['budget_warnings_title']}")
        for item in warnings:
            lines.append(f"- {item}")
    suggestions = budget.get("suggestions") or []
    if suggestions:
        lines.append("")
        lines.append(f"## {txt['budget_suggestions_title']}")
        for item in suggestions:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _markdown_for_savings(plan: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['savings_title']}"]
    summary = plan.get("summary") or ""
    if summary:
        lines.append("")
        lines.append(summary)
    currency = plan.get("currency") or ""
    lines.append("")
    lines.append(f"- {txt['savings_card_monthly']}: {plan.get('monthly_contribution', 0)} {currency}")
    lines.append(f"- {txt['savings_card_months']}: {plan.get('months_to_goal', 0)}")
    lines.append(f"- {txt['savings_card_percent']}: {plan.get('percent_of_income', 0)}%")
    milestones = plan.get("milestones") or []
    if milestones:
        lines.append("")
        lines.append(f"## {txt['savings_milestones_title']}")
        for m in milestones:
            lines.append(
                f"- {m.get('label', '')} - {m.get('amount', 0)} {currency} ({m.get('after_months', 0)} mo)"
            )
    tips = plan.get("tips") or []
    if tips:
        lines.append("")
        lines.append(f"## {txt['savings_tips_title']}")
        for tip in tips:
            lines.append(f"- {tip}")
    return "\n".join(lines)


def _markdown_for_investments(scenario: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['invest_title']}"]
    currency = scenario.get("currency") or ""
    amount = scenario.get("amount") or 0
    horizon = scenario.get("horizon_years") or 0
    lines.append("")
    lines.append(f"**Amount**: {amount} {currency} - **Horizon**: {horizon} years")
    lines.append("")
    for s_data in scenario.get("scenarios") or []:
        lines.append(f"## {s_data.get('name', '')}")
        lines.append(f"- {txt['invest_scenario_return']}: {s_data.get('expected_annual_return_pct', 0)}%")
        lines.append(f"- {txt['invest_scenario_projected']}: {s_data.get('projected_value', 0)} {currency}")
        lines.append(f"- {s_data.get('description', '')}")
        lines.append(f"### {txt['invest_scenario_allocation']}")
        for alloc in s_data.get("allocation") or []:
            lines.append(f"- {alloc.get('asset_class', '')}: {alloc.get('percent', 0)}%")
        lines.append("")
    if scenario.get("diversification_note"):
        lines.append(f"## {txt['invest_diversification_title']}")
        lines.append(scenario["diversification_note"])
        lines.append("")
    if scenario.get("risk_note"):
        lines.append(f"## {txt['invest_risk_title']}")
        lines.append(scenario["risk_note"])
        lines.append("")
    if scenario.get("disclaimer"):
        lines.append(f"> {scenario['disclaimer']}")
    return "\n".join(lines)


def _markdown_for_expense_analysis(analysis: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['analysis_title']}"]
    summary = analysis.get("summary") or ""
    if summary:
        lines.append("")
        lines.append(summary)
    currency = analysis.get("currency") or ""
    lines.append("")
    lines.append(f"- {txt['analysis_totals_income']}: {analysis.get('total_income', 0)} {currency}")
    lines.append(f"- {txt['analysis_totals_expenses']}: {analysis.get('total_expenses', 0)} {currency}")
    lines.append(f"- {txt['analysis_totals_net']}: {analysis.get('net_cash_flow', 0)} {currency}")
    if analysis.get("period"):
        lines.append(f"- {analysis['period']}")
    cats = analysis.get("categories") or []
    if cats:
        lines.append("")
        lines.append(f"## {txt['analysis_categories_title']}")
        for c in cats:
            lines.append(
                f"- {c.get('name', '')} - {c.get('amount', 0)} {currency} ({c.get('percent_of_expenses', 0)}%)"
            )
    top = analysis.get("top_outflows") or []
    if top:
        lines.append("")
        lines.append(f"## {txt['analysis_top_outflows_title']}")
        for entry in top:
            lines.append(
                f"- {entry.get('label', '')} - {entry.get('amount', 0)} {currency} - {entry.get('note', '')}"
            )
    rec = analysis.get("recurring") or []
    if rec:
        lines.append("")
        lines.append(f"## {txt['analysis_recurring_title']}")
        for entry in rec:
            lines.append(
                f"- {entry.get('label', '')} - {entry.get('monthly_amount', 0)} {currency} / {entry.get('category', '')}"
            )
    suggestions = analysis.get("suggestions") or []
    if suggestions:
        lines.append("")
        lines.append(f"## {txt['analysis_suggestions_title']}")
        for s_item in suggestions:
            lines.append(f"- {s_item}")
    return "\n".join(lines)


def _markdown_for_tax(plan: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['taxes_title']} - {plan.get('country', '')}"]
    lines.append("")
    lines.append(
        f"**{txt['form_currency']}**: {plan.get('filing_status', '')} - {plan.get('year', '')}"
    )
    if plan.get("checklist"):
        lines.append("")
        lines.append(f"## {txt['taxes_checklist_title']}")
        for item in plan["checklist"]:
            lines.append(f"- **{item.get('title', '')}** - {item.get('detail', '')}")
    if plan.get("deadlines"):
        lines.append("")
        lines.append(f"## {txt['taxes_deadlines_title']}")
        for d in plan["deadlines"]:
            lines.append(f"- {d.get('label', '')}: {d.get('date_or_window', '')}")
    if plan.get("documents_needed"):
        lines.append("")
        lines.append(f"## {txt['taxes_documents_title']}")
        for d in plan["documents_needed"]:
            lines.append(f"- {d}")
    if plan.get("tips"):
        lines.append("")
        lines.append(f"## {txt['taxes_tips_title']}")
        for tip in plan["tips"]:
            lines.append(f"- {tip}")
    if plan.get("disclaimer"):
        lines.append("")
        lines.append(f"> {plan['disclaimer']}")
    return "\n".join(lines)


def _markdown_for_insurance(plan: dict, *, output_lang: str) -> str:
    txt = s(output_lang)
    lines = [f"# {txt['insurance_title']} - {plan.get('household', '')}"]
    if plan.get("summary"):
        lines.append("")
        lines.append(plan["summary"])
    if plan.get("policies"):
        lines.append("")
        lines.append(f"## {txt['insurance_policies_title']}")
        for p in plan["policies"]:
            lines.append(
                f"- **{p.get('name', '')}** ({p.get('kind', '')}) - {p.get('limit_note', '')} - {p.get('premium_note', '')}"
            )
    if plan.get("coverage_gaps"):
        lines.append("")
        lines.append(f"## {txt['insurance_gaps_title']}")
        for g in plan["coverage_gaps"]:
            lines.append(
                f"- ({g.get('severity', '')}) **{g.get('topic', '')}** - {g.get('risk', '')}"
            )
    if plan.get("duplicates"):
        lines.append("")
        lines.append(f"## {txt['insurance_duplicates_title']}")
        for d in plan["duplicates"]:
            lines.append(f"- {d}")
    if plan.get("watch_outs"):
        lines.append("")
        lines.append(f"## {txt['insurance_watch_outs_title']}")
        for w in plan["watch_outs"]:
            lines.append(f"- {w}")
    if plan.get("suggestions"):
        lines.append("")
        lines.append(f"## {txt['insurance_suggestions_title']}")
        for sug in plan["suggestions"]:
            lines.append(f"- {sug}")
    if plan.get("disclaimer"):
        lines.append("")
        lines.append(f"> {plan['disclaimer']}")
    return "\n".join(lines)


def save_full_analysis(*, output_lang: str) -> PipelineResult:
    """Persist every cached analysis to a fresh run folder.

    Each run writes Markdown + PDF for every populated analysis plus a
    ``summary.json`` that mirrors the cached structured outputs. The
    history index in ``~/AI Hub/history.json`` gains a row so the
    right-hand "Recent analyses" card can display the run without
    re-reading the disk.
    """
    output_lang = _resolve_lang(output_lang)
    if not STATE.has_any_analysis():
        return _set_error(
            "save_full_analysis",
            s(output_lang)["menu_save_no_run"],
        )

    _set_activity("exporting")
    try:
        run_dir = store.new_run_dir("ai-finance", "", section="ai_finance")
    except Exception as exc:
        return _set_error("save_full_analysis", str(exc))

    docs_written: list[str] = []
    payload: dict[str, Any] = {"created": datetime.now().isoformat()}
    pairs: list[tuple[str, str, dict, Callable[[dict, str], str]]] = []
    if STATE.budget is not None:
        pairs.append(("Budget", "budget", STATE.budget, _markdown_for_budget))
    if STATE.savings_plan is not None:
        pairs.append(("Savings_plan", "savings_plan", STATE.savings_plan, _markdown_for_savings))
    if STATE.investment_scenario is not None:
        pairs.append(("Investment_scenarios", "investment_scenario", STATE.investment_scenario, _markdown_for_investments))
    if STATE.expense_analysis is not None:
        pairs.append(("Expense_analysis", "expense_analysis", STATE.expense_analysis, _markdown_for_expense_analysis))
    if STATE.tax_checklist is not None:
        pairs.append(("Tax_checklist", "tax_checklist", STATE.tax_checklist, _markdown_for_tax))
    if STATE.insurance_review is not None:
        pairs.append(("Insurance_review", "insurance_review", STATE.insurance_review, _markdown_for_insurance))

    for basename, key, data, md_builder in pairs:
        try:
            md_text = md_builder(data, output_lang=output_lang)
            exporter.export_markdown(md_text, run_dir / f"{basename}.md")
            try:
                exporter.export_pdf(md_text, run_dir / f"{basename}.pdf", title=basename)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.pipeline", f"save_full_analysis_pdf_{key}_failed", exc
                )
            docs_written.append(basename)
            payload[key] = data
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.pipeline", f"save_full_analysis_export_{key}_failed", exc
            )

    try:
        store.write_json_file(run_dir, "summary.json", payload)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", "save_full_analysis_summary_failed", exc
        )

    summary = store.RunSummary(
        timestamp=datetime.now().isoformat(),
        role="AI Finance",
        company="",
        overall_score=0,
        folder=str(run_dir),
        provider=settings_store.get_provider(),
        model=settings_store.get_model(),
        cost_usd=0.0,
        docs=docs_written,
        note="ai-finance",
    )
    try:
        store.append_run(summary)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", "save_full_analysis_history_failed", exc
        )

    STATE.last_run_folder = str(run_dir)
    STATE.runs_history.insert(0, {
        "timestamp": summary.timestamp,
        "title": "AI Finance",
        "folder": str(run_dir),
        "docs": docs_written,
    })
    STATE.runs_history = STATE.runs_history[:20]
    STATE.activity = "ready"
    REFS.request_context_refresh()
    logger_service.log_event(
        "INFO", "ai_finance.pipeline", "save_full_analysis_done",
        folder=str(run_dir), docs=docs_written,
    )
    return PipelineResult(ok=True)


# -- Markets ----------------------------------------------------------


def refresh_markets() -> None:
    """Pull live tickers for the right-hand Markets card.

    Called from a daemon thread spawned by :mod:`context`. Honours both
    the ``market_data_enabled`` kill-switch and the user-customised
    ticker list from
    :func:`src.services.settings_store.get_finance_tickers`. When the
    list is empty (or the toggle is off) we clear ``STATE.markets`` and
    skip the fetch - the card paints its own empty state.
    """
    from src.services import market_data

    if not settings_store.get_market_data_enabled():
        STATE.markets = []
        STATE.markets_loading = False
        STATE.markets_error = ""
        REFS.request_context_refresh()
        return

    symbols = settings_store.get_finance_tickers()
    if not symbols:
        STATE.markets = []
        STATE.markets_loading = False
        STATE.markets_error = ""
        REFS.request_context_refresh()
        return

    STATE.markets_loading = True
    REFS.request_context_refresh()
    try:
        name_hints = {sym: name for sym, name, _color in finance_data.DEFAULT_TICKERS}
        quotes = market_data.get_quotes(symbols, name_hints=name_hints)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.pipeline", "refresh_markets_failed", exc
        )
        STATE.markets = []
        STATE.markets_error = str(exc)
        STATE.markets_loading = False
        REFS.request_context_refresh()
        return
    if not quotes:
        # ``yfinance`` returned an empty list - typically the user is
        # offline, a corporate proxy is blocking Yahoo, or the symbol
        # set is misspelled. Without surfacing this the card just shows
        # the generic "data zatím nedorazila" hint forever, which looks
        # like a frontend bug; promote it to a real error string so the
        # card renders an actionable message instead.
        STATE.markets = []
        STATE.markets_fetched_at = time.time()
        STATE.markets_loading = False
        STATE.markets_error = "markets_empty_response"
        logger_service.log_event(
            "WARNING", "ai_finance.pipeline", "refresh_markets_empty",
            requested=len(symbols),
        )
        REFS.request_context_refresh()
        return

    STATE.markets = [
        {
            "symbol": q.symbol,
            "name": q.name,
            "last": q.last,
            "change_pct": q.change_pct,
            "trend": q.trend,
            "spark": q.spark,
        }
        for q in quotes
    ]
    STATE.markets_fetched_at = time.time()
    STATE.markets_loading = False
    STATE.markets_error = ""
    REFS.request_context_refresh()
