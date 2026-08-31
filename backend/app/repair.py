from __future__ import annotations

from typing import Iterable

from .models import (
    Itinerary,
    PlanRequest,
    RepairAction,
    RepairAttempt,
    RepairResult,
    ValidationFailure,
    Venue,
)
from .validator import (
    validation_has_errors,
)


Coordinates = tuple[float, float]

DEFAULT_MAX_REPAIR_ATTEMPTS = 3


def error_failures(
    itinerary: Itinerary,
) -> list[ValidationFailure]:
    """
    Return only hard validation errors.

    Warning-level issues do not trigger automatic repair.
    """
    return [
        failure
        for failure
        in itinerary.validation_failures
        if failure.severity == "error"
    ]


def failure_codes(
    failures: Iterable[
        ValidationFailure
    ],
) -> list[str]:
    """
    Return unique validation failure codes while preserving order.
    """
    result: list[str] = []

    for failure in failures:
        if failure.code not in result:
            result.append(
                failure.code
            )

    return result


def stop_names(
    itinerary: Itinerary,
) -> set[str]:
    """
    Return the names of venues already used by the itinerary.
    """
    return {
        stop.name
        for stop in itinerary.stops
    }


def venue_lookup(
    venues: list[Venue],
) -> dict[str, Venue]:
    """
    Build a name-to-Venue mapping.
    """
    return {
        venue.name: venue
        for venue in venues
    }


def itinerary_venues(
    itinerary: Itinerary,
    venues: list[Venue],
) -> list[Venue]:
    """
    Recover Venue objects represented by an itinerary.
    """
    lookup = venue_lookup(
        venues
    )

    result: list[Venue] = []

    for stop in itinerary.stops:
        venue = lookup.get(
            stop.name
        )

        if venue is None:
            return []

        result.append(
            venue
        )

    return result


def replacement_candidates(
    *,
    target: Venue,
    itinerary: Itinerary,
    venues: list[Venue],
) -> list[Venue]:
    """
    Find alternative venues for one stop.

    Replacements must:
    - have the same category
    - not already exist in the itinerary
    - not be the current target
    """
    used_names = stop_names(
        itinerary
    )

    return [
        venue
        for venue in venues
        if (
            venue.category
            == target.category
            and venue.name
            != target.name
            and venue.name
            not in used_names
        )
    ]


def choose_budget_replacement(
    *,
    target: Venue,
    itinerary: Itinerary,
    venues: list[Venue],
) -> Venue | None:
    """
    Choose the cheapest available same-category replacement.
    """
    candidates = replacement_candidates(
        target=target,
        itinerary=itinerary,
        venues=venues,
    )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda venue: (
            venue.estimated_cost_per_person,
            venue.duration_minutes,
            venue.name,
        ),
    )


def coordinate_distance_score(
    venue_a: Venue,
    venue_b: Venue,
) -> float:
    """
    Cheap local geographic score used only for replacement ranking.

    Lower is better.

    This avoids external routing calls during repair-strategy
    selection.
    """
    if (
        venue_a.latitude is None
        or venue_a.longitude is None
        or venue_b.latitude is None
        or venue_b.longitude is None
    ):
        if venue_a.area == venue_b.area:
            return 0.0

        return 1000.0

    latitude_delta = (
        venue_a.latitude
        - venue_b.latitude
    )

    longitude_delta = (
        venue_a.longitude
        - venue_b.longitude
    )

    return (
        latitude_delta
        * latitude_delta
        + longitude_delta
        * longitude_delta
    )


def choose_nearby_replacement(
    *,
    target: Venue,
    previous_venue: Venue | None,
    itinerary: Itinerary,
    venues: list[Venue],
) -> Venue | None:
    """
    Choose a geographically closer same-category replacement.

    Preference order:
    1. close to the previous stop
    2. same area
    3. lower cost
    """
    candidates = replacement_candidates(
        target=target,
        itinerary=itinerary,
        venues=venues,
    )

    if not candidates:
        return None

    if previous_venue is None:
        return min(
            candidates,
            key=lambda venue: (
                venue.area
                != target.area,
                venue.estimated_cost_per_person,
                venue.name,
            ),
        )

    return min(
        candidates,
        key=lambda venue: (
            coordinate_distance_score(
                previous_venue,
                venue,
            ),
            venue.area
            != previous_venue.area,
            venue.estimated_cost_per_person,
            venue.name,
        ),
    )


def choose_closed_venue_replacement(
    *,
    target: Venue,
    itinerary: Itinerary,
    venues: list[Venue],
) -> Venue | None:
    """
    Replace a confirmed closed venue.

    Prefer:
    1. same category
    2. known opening-hours data
    3. same area
    4. lower cost
    """
    candidates = replacement_candidates(
        target=target,
        itinerary=itinerary,
        venues=venues,
    )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda venue: (
            not bool(
                venue.opening_hours
            ),
            venue.area
            != target.area,
            venue.estimated_cost_per_person,
            venue.name,
        ),
    )


def most_expensive_venue(
    itinerary: Itinerary,
    venues: list[Venue],
) -> Venue | None:
    """
    Find the most expensive venue currently used by the plan.
    """
    current_venues = itinerary_venues(
        itinerary,
        venues,
    )

    if not current_venues:
        return None

    return max(
        current_venues,
        key=lambda venue: (
            venue.estimated_cost_per_person,
            venue.name,
        ),
    )


def venue_for_name(
    name: object,
    venues: list[Venue],
) -> Venue | None:
    """
    Safely resolve a venue name from structured failure details.
    """
    if not isinstance(
        name,
        str,
    ):
        return None

    return venue_lookup(
        venues
    ).get(
        name
    )


def previous_venue_for_target(
    *,
    target_name: str,
    itinerary: Itinerary,
    venues: list[Venue],
) -> Venue | None:
    """
    Return the itinerary venue immediately before the target.
    """
    current_venues = itinerary_venues(
        itinerary,
        venues,
    )

    for index, venue in enumerate(
        current_venues
    ):
        if venue.name != target_name:
            continue

        if index == 0:
            return None

        return current_venues[
            index - 1
        ]

    return None


def choose_action_for_failure(
    *,
    failure: ValidationFailure,
    itinerary: Itinerary,
    venues: list[Venue],
) -> RepairAction:
    """
    Convert one structured validation error into one repair action.
    """
    if (
        failure.code
        == "budget_exceeded"
    ):
        target = most_expensive_venue(
            itinerary,
            venues,
        )

        if target is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                rationale=(
                    "The repair agent could not "
                    "resolve the itinerary venues."
                ),
            )

        replacement = (
            choose_budget_replacement(
                target=target,
                itinerary=itinerary,
                venues=venues,
            )
        )

        if replacement is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                target_name=target.name,
                rationale=(
                    "No cheaper same-category "
                    "replacement was available."
                ),
            )

        return RepairAction(
            failure_code=failure.code,
            strategy=(
                "replace_expensive_venue"
            ),
            target_name=target.name,
            replacement_name=(
                replacement.name
            ),
            rationale=(
                "Replace the most expensive "
                "stop with a cheaper "
                "same-category venue."
            ),
            metadata={
                "old_cost_per_person": (
                    target
                    .estimated_cost_per_person
                ),
                "new_cost_per_person": (
                    replacement
                    .estimated_cost_per_person
                ),
            },
        )

    if (
        failure.code
        == "travel_leg_too_long"
    ):
        target = venue_for_name(
            failure.details.get(
                "to_name"
            ),
            venues,
        )

        if target is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                rationale=(
                    "The distant destination "
                    "could not be resolved."
                ),
            )

        previous_venue = (
            previous_venue_for_target(
                target_name=target.name,
                itinerary=itinerary,
                venues=venues,
            )
        )

        replacement = (
            choose_nearby_replacement(
                target=target,
                previous_venue=previous_venue,
                itinerary=itinerary,
                venues=venues,
            )
        )

        if replacement is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                target_name=target.name,
                rationale=(
                    "No nearby same-category "
                    "replacement was available."
                ),
            )

        return RepairAction(
            failure_code=failure.code,
            strategy=(
                "replace_distant_venue"
            ),
            target_name=target.name,
            replacement_name=(
                replacement.name
            ),
            rationale=(
                "Replace the destination of "
                "the long travel leg with a "
                "closer same-category venue."
            ),
            metadata={
                "actual_minutes": (
                    failure.details.get(
                        "actual_minutes"
                    )
                ),
                "max_minutes": (
                    failure.details.get(
                        "max_minutes"
                    )
                ),
            },
        )

    if (
        failure.code
        == "venue_closed"
    ):
        target = venue_for_name(
            failure.details.get(
                "venue_name"
            ),
            venues,
        )

        if target is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                rationale=(
                    "The closed venue could "
                    "not be resolved."
                ),
            )

        replacement = (
            choose_closed_venue_replacement(
                target=target,
                itinerary=itinerary,
                venues=venues,
            )
        )

        if replacement is None:
            return RepairAction(
                failure_code=failure.code,
                strategy="no_action",
                target_name=target.name,
                rationale=(
                    "No alternative "
                    "same-category venue "
                    "was available."
                ),
            )

        return RepairAction(
            failure_code=failure.code,
            strategy=(
                "replace_closed_venue"
            ),
            target_name=target.name,
            replacement_name=(
                replacement.name
            ),
            rationale=(
                "Replace the confirmed closed "
                "venue with an available "
                "same-category alternative."
            ),
        )

    return RepairAction(
        failure_code=failure.code,
        strategy="no_action",
        rationale=(
            "This failure does not currently "
            "have an automatic repair strategy."
        ),
    )


def choose_repair_actions(
    *,
    itinerary: Itinerary,
    venues: list[Venue],
) -> list[RepairAction]:
    """
    Select repair actions from the itinerary's current errors.

    At most one action is produced for each failure code during one
    repair iteration.
    """
    failures = error_failures(
        itinerary
    )

    actions: list[
        RepairAction
    ] = []

    handled_codes: set[str] = set()

    for failure in failures:
        if (
            failure.code
            in handled_codes
        ):
            continue

        action = choose_action_for_failure(
            failure=failure,
            itinerary=itinerary,
            venues=venues,
        )

        actions.append(
            action
        )

        handled_codes.add(
            failure.code
        )

    return actions


def apply_repair_actions(
    *,
    itinerary: Itinerary,
    venues: list[Venue],
    actions: list[RepairAction],
) -> list[Venue]:
    """
    Apply replacement actions to the itinerary's Venue sequence.
    """
    current_venues = itinerary_venues(
        itinerary,
        venues,
    )

    if not current_venues:
        return []

    lookup = venue_lookup(
        venues
    )

    replacements: dict[
        str,
        Venue,
    ] = {}

    for action in actions:
        if (
            action.strategy
            == "no_action"
        ):
            continue

        if (
            action.target_name is None
            or action.replacement_name
            is None
        ):
            continue

        replacement = lookup.get(
            action.replacement_name
        )

        if replacement is None:
            continue

        replacements[
            action.target_name
        ] = replacement

    return [
        replacements.get(
            venue.name,
            venue,
        )
        for venue in current_venues
    ]


def repaired_plan_is_better(
    *,
    before: Itinerary,
    after: Itinerary,
) -> bool:
    """
    Decide whether a repair attempt represents progress.

    Priority:
    1. fewer hard errors
    2. fewer total validation issues
    3. higher planner score
    """
    before_errors = len(
        error_failures(
            before
        )
    )

    after_errors = len(
        error_failures(
            after
        )
    )

    if (
        after_errors
        < before_errors
    ):
        return True

    if (
        after_errors
        > before_errors
    ):
        return False

    before_failures = len(
        before.validation_failures
    )

    after_failures = len(
        after.validation_failures
    )

    if (
        after_failures
        < before_failures
    ):
        return True

    if (
        after_failures
        > before_failures
    ):
        return False

    return (
        after.score
        > before.score
    )


def repair_itinerary(
    *,
    request: PlanRequest,
    itinerary: Itinerary,
    venues: list[Venue],
    start_coordinates: (
        Coordinates
        | None
    ) = None,
    max_attempts: int = (
        DEFAULT_MAX_REPAIR_ATTEMPTS
    ),
    prefer_live: bool = False,
) -> RepairResult:
    """
    Run PlanPilot's bounded deterministic agentic repair loop.

    The loop is:

        inspect errors
            ->
        choose actions
            ->
        modify venue selection
            ->
        rebuild itinerary
            ->
        revalidate
            ->
        repeat

    The process stops when:
    - no hard errors remain
    - no repair action is possible
    - a repair does not improve the plan
    - max_attempts is reached

    The planner import is intentionally local so planner.py can use
    this repair module without creating a circular import.
    """
    from .planner import build_itinerary

    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be "
            "at least 1."
        )

    original_itinerary = (
        itinerary.model_copy(
            deep=True
        )
    )

    current_itinerary = (
        itinerary.model_copy(
            deep=True
        )
    )

    attempts: list[
        RepairAttempt
    ] = []

    if not validation_has_errors(
        current_itinerary
        .validation_failures
    ):
        return RepairResult(
            success=True,
            original_itinerary=(
                original_itinerary
            ),
            final_itinerary=(
                current_itinerary
            ),
            attempts=[],
            max_attempts=max_attempts,
            exhausted=False,
        )

    for attempt_number in range(
        1,
        max_attempts + 1,
    ):
        current_errors = (
            error_failures(
                current_itinerary
            )
        )

        actions = (
            choose_repair_actions(
                itinerary=(
                    current_itinerary
                ),
                venues=venues,
            )
        )

        actionable = [
            action
            for action in actions
            if (
                action.strategy
                != "no_action"
            )
        ]

        if not actionable:
            attempts.append(
                RepairAttempt(
                    attempt_number=(
                        attempt_number
                    ),
                    input_plan_title=(
                        current_itinerary
                        .title
                    ),
                    failure_codes=[
                        failure.code
                        for failure
                        in current_errors
                    ],
                    actions=actions,
                    output_plan_title=None,
                    remaining_failures=(
                        current_itinerary
                        .validation_failures
                    ),
                    success=False,
                )
            )

            return RepairResult(
                success=False,
                original_itinerary=(
                    original_itinerary
                ),
                final_itinerary=(
                    current_itinerary
                ),
                attempts=attempts,
                max_attempts=(
                    max_attempts
                ),
                exhausted=False,
            )

        repaired_venues = (
            apply_repair_actions(
                itinerary=(
                    current_itinerary
                ),
                venues=venues,
                actions=actions,
            )
        )

        if not repaired_venues:
            attempts.append(
                RepairAttempt(
                    attempt_number=(
                        attempt_number
                    ),
                    input_plan_title=(
                        current_itinerary
                        .title
                    ),
                    failure_codes=[
                        failure.code
                        for failure
                        in current_errors
                    ],
                    actions=actions,
                    output_plan_title=None,
                    remaining_failures=(
                        current_itinerary
                        .validation_failures
                    ),
                    success=False,
                )
            )

            return RepairResult(
                success=False,
                original_itinerary=(
                    original_itinerary
                ),
                final_itinerary=(
                    current_itinerary
                ),
                attempts=attempts,
                max_attempts=(
                    max_attempts
                ),
                exhausted=False,
            )

        repaired_itinerary = (
            build_itinerary(
                request=request,
                chosen_venues=(
                    repaired_venues
                ),
                start_coordinates=(
                    start_coordinates
                ),
                prefer_live=prefer_live,
            )
        )

        success = not (
            validation_has_errors(
                repaired_itinerary
                .validation_failures
            )
        )

        attempts.append(
            RepairAttempt(
                attempt_number=(
                    attempt_number
                ),
                input_plan_title=(
                    current_itinerary
                    .title
                ),
                failure_codes=[
                    failure.code
                    for failure
                    in current_errors
                ],
                actions=actions,
                output_plan_title=(
                    repaired_itinerary
                    .title
                ),
                remaining_failures=(
                    repaired_itinerary
                    .validation_failures
                ),
                success=success,
            )
        )

        if success:
            return RepairResult(
                success=True,
                original_itinerary=(
                    original_itinerary
                ),
                final_itinerary=(
                    repaired_itinerary
                ),
                attempts=attempts,
                max_attempts=(
                    max_attempts
                ),
                exhausted=False,
            )

        if not repaired_plan_is_better(
            before=current_itinerary,
            after=repaired_itinerary,
        ):
            return RepairResult(
                success=False,
                original_itinerary=(
                    original_itinerary
                ),
                final_itinerary=(
                    repaired_itinerary
                ),
                attempts=attempts,
                max_attempts=(
                    max_attempts
                ),
                exhausted=False,
            )

        current_itinerary = (
            repaired_itinerary
        )

    return RepairResult(
        success=False,
        original_itinerary=(
            original_itinerary
        ),
        final_itinerary=(
            current_itinerary
        ),
        attempts=attempts,
        max_attempts=max_attempts,
        exhausted=True,
    )
