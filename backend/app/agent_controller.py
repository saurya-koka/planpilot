from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from .agent_models import (
    AgentDecision,
    AgentRunResult,
    AgentStep,
    AgentToolCall,
    ToolExecutionRecord,
)
from .agent_tools import (
    OPENAI_AGENT_TOOLS,
    AgentToolContext,
    execute_agent_tool,
)
from .models import (
    Itinerary,
    PlanRequest,
    Venue,
)


load_dotenv()


DEFAULT_MAX_AGENT_STEPS = 8


SYSTEM_PROMPT = """
You are the PlanPilot orchestration controller.

Your job is not to invent itinerary facts yourself.

You coordinate deterministic PlanPilot tools.

Available behavior:

1. build_plans
   Generate itinerary candidates.

2. validate_plan
   Inspect the validation state of one candidate.

3. repair_plan
   Repair one candidate containing hard validation errors.

4. search_venues
   Search for venue options when additional choices are required.

Important rules:

- Prefer deterministic PlanPilot tools over making claims yourself.
- Do not invent venue availability, prices, routes, or validation results.
- Use build_plans before trying to validate or repair a plan unless
  candidates already exist.
- When candidates contain hard validation errors, use repair_plan.
- Warning-level validation failures do not necessarily require repair.
- Never repeat the same tool call with identical arguments after it
  has already been attempted.
- If repair fails, try a different plan or use search_venues instead
  of retrying the identical repair.
- Finish when at least one usable plan exists and no further tool call
  is necessary.
- Keep reasoning concise.
""".strip()


def agent_is_configured() -> bool:
    """
    Return True when an OpenAI API key is available.
    """
    return bool(
        os.getenv(
            "OPENAI_API_KEY"
        )
    )


def plan_has_hard_errors(
    plan: Itinerary,
) -> bool:
    """
    Return True when a plan contains at least one error-severity
    validation failure.
    """
    return any(
        failure.severity
        == "error"
        for failure
        in plan.validation_failures
    )


def has_usable_plan(
    plans: list[Itinerary],
) -> bool:
    """
    Return True when at least one candidate is free of hard errors.

    Warnings are allowed.

    This is the correct definition of an agent success state.
    """
    return any(
        not plan_has_hard_errors(
            plan
        )
        for plan in plans
    )


def all_plans_error_free(
    plans: list[Itinerary],
) -> bool:
    """
    Return True only when every available plan has no hard errors.
    """
    if not plans:
        return False

    return all(
        not plan_has_hard_errors(
            plan
        )
        for plan in plans
    )


def build_agent_state_summary(
    context: AgentToolContext,
) -> dict[str, Any]:
    """
    Build a compact representation of the Python-owned state.

    The LLM sees enough information to choose the next tool but does
    not own or mutate the actual PlanPilot objects.
    """
    return {
        "request": (
            context.request
            .model_dump()
        ),
        "candidate_count": len(
            context.plans
        ),
        "usable_candidate_count": sum(
            1
            for plan
            in context.plans
            if not plan_has_hard_errors(
                plan
            )
        ),
        "candidates": [
            {
                "index": index,
                "title": plan.title,
                "label": plan.label,
                "total_cost": (
                    plan.total_cost
                ),
                "score": (
                    plan.score
                ),
                "has_hard_errors": (
                    plan_has_hard_errors(
                        plan
                    )
                ),
                "validation_failures": [
                    {
                        "code": (
                            failure.code
                        ),
                        "severity": (
                            failure.severity
                        ),
                    }
                    for failure
                    in plan
                    .validation_failures
                ],
            }
            for index, plan
            in enumerate(
                context.plans
            )
        ],
    }


def make_initial_input(
    *,
    user_message: str,
    context: AgentToolContext,
) -> list[dict[str, Any]]:
    """
    Build the first Responses API input.
    """
    state = (
        build_agent_state_summary(
            context
        )
    )

    return [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
            ),
        },
        {
            "role": "user",
            "content": (
                "User request:\n"
                f"{user_message}\n\n"
                "Current PlanPilot state:\n"
                f"{json.dumps(state)}"
            ),
        },
    ]


def extract_function_calls(
    response: Any,
) -> list[AgentToolCall]:
    """
    Convert OpenAI Responses API function-call items into PlanPilot
    AgentToolCall models.

    Function-call arguments arrive as a JSON string.
    """
    calls: list[
        AgentToolCall
    ] = []

    output_items = getattr(
        response,
        "output",
        [],
    )

    for item in output_items:
        if (
            getattr(
                item,
                "type",
                None,
            )
            != "function_call"
        ):
            continue

        name = getattr(
            item,
            "name",
            None,
        )

        call_id = getattr(
            item,
            "call_id",
            None,
        )

        raw_arguments = getattr(
            item,
            "arguments",
            "{}",
        )

        if (
            not isinstance(
                name,
                str,
            )
            or not isinstance(
                call_id,
                str,
            )
        ):
            continue

        try:
            arguments = json.loads(
                raw_arguments
            )

        except (
            TypeError,
            json.JSONDecodeError,
        ):
            arguments = {}

        if not isinstance(
            arguments,
            dict,
        ):
            arguments = {}

        try:
            call = AgentToolCall(
                call_id=call_id,
                tool_name=name,
                arguments=arguments,
                rationale="",
            )

        except Exception:
            continue

        calls.append(
            call
        )

    return calls


def response_text(
    response: Any,
) -> str:
    """
    Safely return response.output_text.
    """
    value = getattr(
        response,
        "output_text",
        "",
    )

    if not isinstance(
        value,
        str,
    ):
        return ""

    return value.strip()


def tool_output_input(
    *,
    call_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one deterministic tool result into a Responses API
    function_call_output item.
    """
    return {
        "type": (
            "function_call_output"
        ),
        "call_id": call_id,
        "output": json.dumps(
            payload,
            default=str,
        ),
    }


def tool_call_signature(
    call: AgentToolCall,
) -> str:
    """
    Create a stable signature for one tool call.

    call_id is deliberately excluded because OpenAI creates a new
    call_id each time even when the tool name and arguments are
    identical.

    Example:

        repair_plan
        {"max_attempts": 3, "plan_index": 0}
    """
    normalized_arguments = (
        json.dumps(
            call.arguments,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            default=str,
        )
    )

    return (
        f"{call.tool_name}:"
        f"{normalized_arguments}"
    )


def duplicate_call_record(
    *,
    call: AgentToolCall,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    """
    Return a structured error instead of executing a duplicate call.
    """
    message = (
        "Duplicate tool call blocked. "
        "This tool was already called "
        "with identical arguments. "
        "Choose a different action."
    )

    record = ToolExecutionRecord(
        call_id=call.call_id,
        tool_name=call.tool_name,
        status="error",
        arguments=(
            call.arguments
        ),
        output_summary=None,
        error_message=message,
    )

    payload = {
        "error": message,
        "duplicate_call": True,
        "tool_name": (
            call.tool_name
        ),
        "arguments": (
            call.arguments
        ),
    }

    return (
        record,
        payload,
    )


def fallback_agent_result(
    *,
    request: PlanRequest,
    venues: list[Venue],
    start_coordinates: (
        tuple[float, float]
        | None
    ),
    max_steps: int,
) -> AgentRunResult:
    """
    Offline fallback used when OpenAI is not configured or the model
    call fails.

    Success is True only when at least one resulting itinerary has
    no hard validation errors.
    """
    from .planner import (
        build_plans,
    )

    plans = build_plans(
        request=request,
        venues=(
            venues
            if venues
            else None
        ),
        start_coordinates=(
            start_coordinates
        ),
    )

    return AgentRunResult(
        success=(
            has_usable_plan(
                plans
            )
        ),
        final_plans=plans,
        steps=[],
        final_message=(
            "Deterministic fallback "
            "planning was used."
        ),
        max_steps=max_steps,
        exhausted=False,
    )


def run_agent(
    *,
    user_message: str,
    request: PlanRequest,
    venues: list[Venue] | None = None,
    start_coordinates: (
        tuple[float, float]
        | None
    ) = None,
    max_steps: int = (
        DEFAULT_MAX_AGENT_STEPS
    ),
) -> AgentRunResult:
    """
    Run the bounded OpenAI tool-calling controller.

    Flow:

        user request
            ->
        model chooses function
            ->
        duplicate check
            ->
        Python validates arguments
            ->
        deterministic tool executes
            ->
        function_call_output
            ->
        model chooses next action
            ->
        repeat

    The loop stops when:
    - the model returns no function calls
    - max_steps is reached
    - the OpenAI call fails

    Success means at least one returned plan has no hard validation
    errors.
    """
    if max_steps < 1:
        raise ValueError(
            "max_steps must be "
            "at least 1."
        )

    context = AgentToolContext(
        request=request,
        venue_source=(
            list(venues)
            if venues
            else []
        ),
        plans=[],
        start_coordinates=(
            start_coordinates
        ),
    )

    if not agent_is_configured():
        return (
            fallback_agent_result(
                request=request,
                venues=(
                    context
                    .venue_source
                ),
                start_coordinates=(
                    start_coordinates
                ),
                max_steps=max_steps,
            )
        )

    try:
        from openai import (
            OpenAI,
        )

        client = OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY"
            )
        )

        model = os.getenv(
            "OPENAI_AGENT_MODEL",
            os.getenv(
                "OPENAI_MODEL",
                "gpt-5",
            ),
        )

        current_input = (
            make_initial_input(
                user_message=(
                    user_message
                ),
                context=context,
            )
        )

        steps: list[
            AgentStep
        ] = []

        previous_response_id: (
            str
            | None
        ) = None

        seen_tool_calls: set[
            str
        ] = set()

        for step_number in range(
            1,
            max_steps + 1,
        ):
            request_kwargs: dict[
                str,
                Any,
            ] = {
                "model": model,
                "input": current_input,
                "tools": (
                    OPENAI_AGENT_TOOLS
                ),
                "tool_choice": "auto",
                "parallel_tool_calls": (
                    False
                ),
            }

            if previous_response_id:
                request_kwargs[
                    "previous_response_id"
                ] = (
                    previous_response_id
                )

            response = (
                client
                .responses
                .create(
                    **request_kwargs
                )
            )

            previous_response_id = (
                getattr(
                    response,
                    "id",
                    None,
                )
            )

            calls = (
                extract_function_calls(
                    response
                )
            )

            if not calls:
                final_text = (
                    response_text(
                        response
                    )
                )

                success = (
                    has_usable_plan(
                        context.plans
                    )
                )

                return AgentRunResult(
                    success=success,
                    final_plans=(
                        context.plans
                    ),
                    steps=steps,
                    final_message=(
                        final_text
                        or (
                            "Agent completed "
                            "without additional "
                            "tool calls."
                        )
                    ),
                    max_steps=max_steps,
                    exhausted=False,
                )

            decision = AgentDecision(
                decision="call_tool",
                rationale=(
                    "The model requested "
                    "one or more PlanPilot "
                    "tools."
                ),
                tool_calls=calls,
            )

            executions: list[
                ToolExecutionRecord
            ] = []

            next_input: list[
                dict[str, Any]
            ] = []

            for call in calls:
                signature = (
                    tool_call_signature(
                        call
                    )
                )

                if (
                    signature
                    in seen_tool_calls
                ):
                    (
                        execution_record,
                        payload,
                    ) = (
                        duplicate_call_record(
                            call=call
                        )
                    )

                else:
                    seen_tool_calls.add(
                        signature
                    )

                    (
                        execution_record,
                        payload,
                    ) = (
                        execute_agent_tool(
                            call=call,
                            context=context,
                        )
                    )

                executions.append(
                    execution_record
                )

                next_input.append(
                    tool_output_input(
                        call_id=(
                            call.call_id
                        ),
                        payload=payload,
                    )
                )

            steps.append(
                AgentStep(
                    step_number=(
                        step_number
                    ),
                    decision=decision,
                    executions=(
                        executions
                    ),
                )
            )

            current_input = (
                next_input
            )

        success = (
            has_usable_plan(
                context.plans
            )
        )

        return AgentRunResult(
            success=success,
            final_plans=(
                context.plans
            ),
            steps=steps,
            final_message=(
                "Agent reached the "
                "maximum step limit."
            ),
            max_steps=max_steps,
            exhausted=True,
        )

    except Exception:
        return (
            fallback_agent_result(
                request=request,
                venues=(
                    context
                    .venue_source
                ),
                start_coordinates=(
                    start_coordinates
                ),
                max_steps=max_steps,
            )
        )
