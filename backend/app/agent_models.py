from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .models import (
    Itinerary,
    PlanRequest,
    ValidationFailure,
    VenueCategory,
)


AgentToolName = Literal[
    "search_venues",
    "build_plans",
    "validate_plan",
    "repair_plan",
]


AgentDecisionType = Literal[
    "call_tool",
    "finish",
]


ToolExecutionStatus = Literal[
    "success",
    "error",
]


class SearchVenuesArguments(BaseModel):
    """
    Structured arguments for the venue-search tool.
    """

    query: str

    city: str

    category: VenueCategory

    limit: int = Field(
        ge=1,
        le=20,
    )


class BuildPlansArguments(BaseModel):
    """
    Structured arguments for generating itinerary candidates.
    """

    request: PlanRequest


class ValidatePlanArguments(BaseModel):
    """
    Structured arguments for validating one existing candidate.

    The agent refers to candidates by their position in its current
    working set rather than trying to regenerate an entire itinerary
    inside the LLM.
    """

    plan_index: int = Field(
        ge=0,
    )


class RepairPlanArguments(BaseModel):
    """
    Structured arguments for invoking the bounded repair engine.
    """

    plan_index: int = Field(
        ge=0,
    )

    max_attempts: int = Field(
        ge=1,
        le=5,
    )


class AgentToolCall(BaseModel):
    """
    Normalized representation of one model-selected tool call.

    The raw OpenAI function call will be converted into this model
    before PlanPilot executes anything.
    """

    call_id: str

    tool_name: AgentToolName

    arguments: dict[
        str,
        object,
    ]

    rationale: str = ""


class AgentDecision(BaseModel):
    """
    One structured decision made by the LLM controller.

    The model either:
        - requests one or more tools
        - finishes because the current result is acceptable
    """

    decision: AgentDecisionType

    rationale: str

    tool_calls: list[
        AgentToolCall
    ] = Field(
        default_factory=list,
    )


class ToolExecutionRecord(BaseModel):
    """
    Record of one deterministic tool execution.

    This gives us an auditable boundary between:
        LLM decision
            ->
        application code execution
    """

    call_id: str

    tool_name: AgentToolName

    status: ToolExecutionStatus

    arguments: dict[
        str,
        object,
    ] = Field(
        default_factory=dict,
    )

    output_summary: str | None = None

    error_message: str | None = None


class AgentStep(BaseModel):
    """
    One complete agent iteration.

    Example:

        step 1
            model chooses search_venues
            tool executes

        step 2
            model chooses build_plans
            tool executes

        step 3
            model decides finish
    """

    step_number: int = Field(
        ge=1,
    )

    decision: AgentDecision

    executions: list[
        ToolExecutionRecord
    ] = Field(
        default_factory=list,
    )


class AgentRunResult(BaseModel):
    """
    Full trace produced by the V2.5 LLM tool-calling controller.
    """

    success: bool

    final_plans: list[
        Itinerary
    ] = Field(
        default_factory=list,
    )

    steps: list[
        AgentStep
    ] = Field(
        default_factory=list,
    )

    final_message: str | None = None

    max_steps: int = Field(
        default=6,
        ge=1,
        le=12,
    )

    exhausted: bool = False


class AgentPlanState(BaseModel):
    """
    Serializable working state passed between agent iterations.

    This prevents the LLM from owning PlanPilot's application state.
    Python owns the real state; the model only sees a controlled
    representation of it.
    """

    request: PlanRequest

    candidate_count: int = Field(
        default=0,
        ge=0,
    )

    candidate_titles: list[
        str
    ] = Field(
        default_factory=list,
    )

    validation_failures: dict[
        int,
        list[
            ValidationFailure
        ],
    ] = Field(
        default_factory=dict,
    )

    completed_tools: list[
        AgentToolName
    ] = Field(
        default_factory=list,
    )


def parse_tool_arguments(
    *,
    tool_name: AgentToolName,
    arguments: dict[
        str,
        object,
    ],
) -> (
    SearchVenuesArguments
    | BuildPlansArguments
    | ValidatePlanArguments
    | RepairPlanArguments
):
    """
    Validate model-generated tool arguments before execution.

    The LLM never gets to send arbitrary dictionaries directly to
    PlanPilot's internal functions.
    """
    if tool_name == "search_venues":
        return (
            SearchVenuesArguments
            .model_validate(
                arguments
            )
        )

    if tool_name == "build_plans":
        return (
            BuildPlansArguments
            .model_validate(
                arguments
            )
        )

    if tool_name == "validate_plan":
        return (
            ValidatePlanArguments
            .model_validate(
                arguments
            )
        )

    if tool_name == "repair_plan":
        return (
            RepairPlanArguments
            .model_validate(
                arguments
            )
        )

    raise ValueError(
        f"Unsupported agent tool: "
        f"{tool_name}"
    )
