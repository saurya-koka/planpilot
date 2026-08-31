from __future__ import annotations

from types import SimpleNamespace

import backend.app.agent_controller as agent_controller

from backend.app.models import (
    PlanRequest,
    Venue,
)


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=200,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=30,
    )


def make_venues() -> list[Venue]:
    return [
        Venue(
            name="Affordable Restaurant",
            category="restaurant",
            area="Back Bay",
            estimated_cost_per_person=30,
            duration_minutes=60,
            vibe=[
                "chill",
            ],
            opening_hours=(
                "Mo-Su 16:00-23:00"
            ),
            source="sample",
        ),
    ]


class FakeResponses:
    """
    Fake OpenAI Responses API.

    Call 1:
        model requests build_plans

    Call 2:
        model returns final text
    """

    def __init__(
        self,
        request: PlanRequest,
    ) -> None:
        self.request = request
        self.call_count = 0
        self.received_kwargs: list[
            dict
        ] = []

    def create(
        self,
        **kwargs,
    ):
        self.call_count += 1

        self.received_kwargs.append(
            kwargs
        )

        if self.call_count == 1:
            return SimpleNamespace(
                id="response-1",
                output=[
                    SimpleNamespace(
                        type=(
                            "function_call"
                        ),
                        name=(
                            "build_plans"
                        ),
                        call_id=(
                            "call-build"
                        ),
                        arguments=(
                            self.request
                            .model_dump_json()
                            if False
                            else (
                                '{"request": '
                                + self.request
                                .model_dump_json()
                                + "}"
                            )
                        ),
                    ),
                ],
                output_text="",
            )

        return SimpleNamespace(
            id="response-2",
            output=[],
            output_text=(
                "I found a usable "
                "PlanPilot itinerary."
            ),
        )


class FakeOpenAIClient:
    def __init__(
        self,
        request: PlanRequest,
    ) -> None:
        self.responses = (
            FakeResponses(
                request
            )
        )


def test_extract_function_calls() -> None:
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="function_call",
                name="validate_plan",
                call_id="call-123",
                arguments=(
                    '{"plan_index": 0}'
                ),
            ),
        ],
    )

    calls = (
        agent_controller
        .extract_function_calls(
            response
        )
    )

    assert len(calls) == 1

    assert (
        calls[0].call_id
        == "call-123"
    )

    assert (
        calls[0].tool_name
        == "validate_plan"
    )

    assert (
        calls[0].arguments
        == {
            "plan_index": 0,
        }
    )


def test_tool_output_input() -> None:
    output = (
        agent_controller
        .tool_output_input(
            call_id="call-1",
            payload={
                "success": True,
            },
        )
    )

    assert output[
        "type"
    ] == "function_call_output"

    assert output[
        "call_id"
    ] == "call-1"

    assert (
        '"success": true'
        in output[
            "output"
        ].lower()
    )


def test_agent_state_summary() -> None:
    request = make_request()

    context = (
        agent_controller
        .AgentToolContext(
            request=request,
            venue_source=(
                make_venues()
            ),
        )
    )

    state = (
        agent_controller
        .build_agent_state_summary(
            context
        )
    )

    assert (
        state[
            "candidate_count"
        ]
        == 0
    )

    assert (
        state[
            "request"
        ][
            "city"
        ]
        == "Boston"
    )


def test_fallback_agent_result() -> None:
    request = make_request()

    result = (
        agent_controller
        .fallback_agent_result(
            request=request,
            venues=make_venues(),
            start_coordinates=None,
            max_steps=6,
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.final_plans
    )

    assert (
        result.steps
        == []
    )

    assert (
        "fallback"
        in (
            result
            .final_message
            .lower()
        )
    )


def test_run_agent_uses_fallback_without_api_key(
    monkeypatch,
) -> None:
    request = make_request()

    monkeypatch.setattr(
        agent_controller,
        "agent_is_configured",
        lambda: False,
    )

    result = (
        agent_controller
        .run_agent(
            user_message=(
                "Plan dinner in "
                "Boston."
            ),
            request=request,
            venues=make_venues(),
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.final_plans
    )

    assert (
        result.steps
        == []
    )


def test_run_agent_executes_multistep_tool_loop(
    monkeypatch,
) -> None:
    """
    Prove the controller performs:

        model
          ->
        function call
          ->
        deterministic tool
          ->
        function_call_output
          ->
        model
          ->
        finish
    """
    request = make_request()

    fake_client = (
        FakeOpenAIClient(
            request
        )
    )

    monkeypatch.setattr(
        agent_controller,
        "agent_is_configured",
        lambda: True,
    )

    import openai

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: (
            fake_client
        ),
    )

    result = (
        agent_controller
        .run_agent(
            user_message=(
                "Plan a chill "
                "dinner in Boston."
            ),
            request=request,
            venues=make_venues(),
            max_steps=4,
        )
    )

    assert (
        result.success
        is True
    )

    assert len(
        result.steps
    ) == 1

    assert (
        result.steps[0]
        .decision
        .decision
        == "call_tool"
    )

    assert (
        result.steps[0]
        .decision
        .tool_calls[0]
        .tool_name
        == "build_plans"
    )

    assert (
        result.steps[0]
        .executions[0]
        .status
        == "success"
    )

    assert (
        result.final_plans
    )

    assert (
        result.final_message
        == (
            "I found a usable "
            "PlanPilot itinerary."
        )
    )

    assert (
        fake_client
        .responses
        .call_count
        == 2
    )


def test_multistep_loop_returns_function_output(
    monkeypatch,
) -> None:
    """
    Verify that the second Responses API call receives the result
    of the first tool invocation.
    """
    request = make_request()

    fake_client = (
        FakeOpenAIClient(
            request
        )
    )

    monkeypatch.setattr(
        agent_controller,
        "agent_is_configured",
        lambda: True,
    )

    import openai

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: (
            fake_client
        ),
    )

    agent_controller.run_agent(
        user_message=(
            "Plan dinner."
        ),
        request=request,
        venues=make_venues(),
        max_steps=4,
    )

    assert (
        len(
            fake_client
            .responses
            .received_kwargs
        )
        == 2
    )

    second_call = (
        fake_client
        .responses
        .received_kwargs[1]
    )

    assert (
        second_call[
            "previous_response_id"
        ]
        == "response-1"
    )

    second_input = (
        second_call[
            "input"
        ]
    )

    assert len(
        second_input
    ) == 1

    assert (
        second_input[0][
            "type"
        ]
        == (
            "function_call_output"
        )
    )

    assert (
        second_input[0][
            "call_id"
        ]
        == "call-build"
    )

    assert (
        "candidate_count"
        in second_input[0][
            "output"
        ]
    )


def test_agent_stops_at_max_steps(
    monkeypatch,
) -> None:
    request = make_request()

    class EndlessResponses:
        def __init__(self):
            self.counter = 0

        def create(
            self,
            **kwargs,
        ):
            self.counter += 1

            return SimpleNamespace(
                id=(
                    f"response-"
                    f"{self.counter}"
                ),
                output=[
                    SimpleNamespace(
                        type=(
                            "function_call"
                        ),
                        name=(
                            "build_plans"
                        ),
                        call_id=(
                            f"call-"
                            f"{self.counter}"
                        ),
                        arguments=(
                            '{"request": '
                            + request
                            .model_dump_json()
                            + "}"
                        ),
                    ),
                ],
                output_text="",
            )

    class EndlessClient:
        def __init__(self):
            self.responses = (
                EndlessResponses()
            )

    fake_client = (
        EndlessClient()
    )

    monkeypatch.setattr(
        agent_controller,
        "agent_is_configured",
        lambda: True,
    )

    import openai

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: (
            fake_client
        ),
    )

    result = (
        agent_controller
        .run_agent(
            user_message=(
                "Keep planning."
            ),
            request=request,
            venues=make_venues(),
            max_steps=2,
        )
    )

    assert (
        result.exhausted
        is True
    )

    assert len(
        result.steps
    ) == 2

    assert (
        result.max_steps
        == 2
    )


def test_invalid_max_steps_raises() -> None:
    request = make_request()

    try:
        agent_controller.run_agent(
            user_message=(
                "Plan dinner."
            ),
            request=request,
            venues=make_venues(),
            max_steps=0,
        )

    except ValueError as exc:
        assert (
            "at least 1"
            in str(
                exc
            )
        )

    else:
        raise AssertionError(
            "Expected ValueError."
        )



def test_duplicate_tool_call_is_blocked() -> None:
    call = (
        agent_controller
        .AgentToolCall(
            call_id="call-duplicate",
            tool_name="repair_plan",
            arguments={
                "plan_index": 0,
                "max_attempts": 3,
            },
            rationale="",
        )
    )

    record, payload = (
        agent_controller
        .duplicate_call_record(
            call=call
        )
    )

    assert (
        record.status
        == "error"
    )

    assert (
        payload[
            "duplicate_call"
        ]
        is True
    )

    assert (
        "duplicate"
        in payload[
            "error"
        ].lower()
    )


def test_has_usable_plan_requires_no_hard_errors() -> None:
    request = make_request()

    venues = make_venues()

    from backend.app.planner import (
        build_itinerary,
    )

    valid_plan = (
        build_itinerary(
            request=request,
            chosen_venues=[
                venues[0],
            ],
            start_coordinates=None,
            prefer_live=False,
        )
    )

    assert (
        agent_controller
        .has_usable_plan(
            [
                valid_plan,
            ]
        )
        is True
    )

    broken_request = (
        make_request()
    )

    broken_request.budget_total = 10

    broken_plan = (
        build_itinerary(
            request=broken_request,
            chosen_venues=[
                venues[0],
            ],
            start_coordinates=None,
            prefer_live=False,
        )
    )

    assert any(
        failure.severity
        == "error"
        for failure
        in broken_plan
        .validation_failures
    )

    assert (
        agent_controller
        .has_usable_plan(
            [
                broken_plan,
            ]
        )
        is False
    )
