"""One QuantMind/QMX Copilot over independently scoped ``psess:`` (Story 60.4).

The in-app panel is an optional contract over an app-use session, not GAP-0081
chrome and not a second copilot. Nested invoke does not union grants. Disposing
a panel does not cancel a running JobHandle. App-use may mint ``change_request``
and must not apply — Story 58.4 remains the apply oracle.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.control.primitives import Skill
from qma.core.ontology import ActorId
from qma.core.operations.descriptor import OperationDescriptor
from qma.core.ports.copilot import (
    APP_USE_MAY_APPLY,
    CONTEXT_TRANSFER_KINDS,
    CONTRIBUTION_HIT_IS_GRANT,
    COPILOT_PRODUCT_IDENTITY,
    COPILOT_SEAT_PROFILES,
    ENGINE_RUN_ID_PREFIX,
    ENGINE_RUN_IS_THIRD_CHAT,
    GAP_0081_CHROME_FILLED,
    HOOKS_OVERRIDE_PRIVILEGE_GATE,
    IN_APP_PANEL_IS_CONTRACT,
    IN_APP_PANEL_IS_GAP_0081_CHROME,
    IN_APP_PANEL_IS_SECOND_COPILOT,
    INSTANCE_MAY_OMIT_PANEL,
    PACK_MAY_OMIT_COPILOT_PROFILE,
    PANEL_DISPOSE_CANCELS_JOB_HANDLE,
    PRODUCT_SESSION_ID_PREFIX,
    RECONNECT_REPLAYS_UNACKED_INTENT,
    SECOND_COPILOT_PRODUCT_MINTED,
    SKILLS_GRANT,
    intersect_tool_availability,
    parse_copilot_product_identity,
    privilege_gate_holds,
    refuse_context_transfer,
    refuse_engine_run_as_chat,
    refuse_hooks_override_privilege_gate,
    refuse_panel_as_second_copilot,
    refuse_second_copilot_product,
    refuse_skill_as_grant,
)
from qma.core.ports.jobs import JobHandle
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.discovery.listing import ContributionListingService
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.retry import HostRetryLoop, HostRetryResult
from qma.daemon.sessions.chrome import ProductSessionChrome
from qma.daemon.sessions.grant_binding import BoundSessionGrant
from qma.daemon.sessions.product_session import (
    GAP_0081_CHROME_FILLED as SESSION_GAP_0081_CHROME_FILLED,
)
from qma.daemon.sessions.product_session import (
    PRODUCT_SESSION_TAB_WRITES,
    ProductSession,
    ProductSessionProfile,
    ProductSessionService,
    ReconnectSnapshot,
    refuse_reconnect_replays_intent,
)
from qma.daemon.staging.change_request import (
    ChangeApplyRecord,
    ChangeRequest,
    ChangeRequestFixture,
)
from qma.wire.contribution_listing import refuse_hit_as_grant
from qma.wire.copilot_profile import parse_wire_copilot_profile
from qma.wire.invocation_envelope import (
    BoundInvocation,
    ContributionRecord,
    InstanceRecord,
    InvocationEnvelope,
    PublicCallTransport,
)
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "APP_USE_MAY_APPLY",
    "CONTEXT_TRANSFER_KINDS",
    "COPILOT_PRODUCT_IDENTITY",
    "COPILOT_SEAT_PROFILES",
    "ENGINE_RUN_IS_THIRD_CHAT",
    "HOOKS_OVERRIDE_PRIVILEGE_GATE",
    "INSTANCE_MAY_OMIT_PANEL",
    "IN_APP_PANEL_IS_CONTRACT",
    "IN_APP_PANEL_IS_GAP_0081_CHROME",
    "PACK_MAY_OMIT_COPILOT_PROFILE",
    "PANEL_DISPOSE_CANCELS_JOB_HANDLE",
    "RECONNECT_REPLAYS_UNACKED_INTENT",
    "SECOND_COPILOT_PRODUCT_MINTED",
    "SKILLS_GRANT",
    "CopilotHost",
    "parse_copilot_product_identity",
    "refuse_engine_run_as_chat",
    "refuse_panel_as_second_copilot",
    "refuse_second_copilot_product",
]


_DEFAULT_AS_OF: Final[str] = "2026-09-20T00:00:00Z"
_DEFAULT_CONTRIBUTION: Final[Mapping[str, str]] = MappingProxyType(
    {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
)


@dataclass
class CopilotHost:
    """One copilot product identity over independently scoped ``psess:`` seats."""

    sessions: ProductSessionService = field(default_factory=ProductSessionService)
    jobs: JobHandleService = field(default_factory=JobHandleService)
    listings: ContributionListingService | None = None
    retry_loop: HostRetryLoop = field(default_factory=HostRetryLoop)
    chrome: ProductSessionChrome = field(init=False)
    changes: ChangeRequestFixture = field(init=False)
    _published: set[str] = field(default_factory=set[str], init=False)
    _host_grants: set[str] = field(default_factory=set[str], init=False)
    _healthy: set[str] = field(default_factory=set[str], init=False)

    def __post_init__(self) -> None:
        self.chrome = ProductSessionChrome(sessions=self.sessions)
        self.changes = ChangeRequestFixture(sessions=self.sessions)

    @property
    def identity(self) -> str:
        return COPILOT_PRODUCT_IDENTITY

    @property
    def second_copilot_minted(self) -> bool:
        return SECOND_COPILOT_PRODUCT_MINTED

    @property
    def gap_0081_chrome_filled(self) -> bool:
        return GAP_0081_CHROME_FILLED or SESSION_GAP_0081_CHROME_FILLED

    @property
    def panel_is_contract(self) -> bool:
        return IN_APP_PANEL_IS_CONTRACT

    def identity_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "app_use_may_apply": APP_USE_MAY_APPLY,
                "contribution_hit_is_grant": CONTRIBUTION_HIT_IS_GRANT,
                "engine_run_is_third_chat": ENGINE_RUN_IS_THIRD_CHAT,
                "gap_0081_chrome_filled": self.gap_0081_chrome_filled,
                "hooks_override_privilege_gate": HOOKS_OVERRIDE_PRIVILEGE_GATE,
                "identity": COPILOT_PRODUCT_IDENTITY,
                "in_app_panel_is_contract": IN_APP_PANEL_IS_CONTRACT,
                "in_app_panel_is_gap_0081_chrome": IN_APP_PANEL_IS_GAP_0081_CHROME,
                "in_app_panel_is_second_copilot": IN_APP_PANEL_IS_SECOND_COPILOT,
                "instance_may_omit_panel": INSTANCE_MAY_OMIT_PANEL,
                "pack_may_omit_copilot_profile": PACK_MAY_OMIT_COPILOT_PROFILE,
                "panel_dispose_cancels_job_handle": PANEL_DISPOSE_CANCELS_JOB_HANDLE,
                "reconnect_replays_unacked_intent": RECONNECT_REPLAYS_UNACKED_INTENT,
                "seats": sorted(COPILOT_SEAT_PROFILES),
                "second_copilot_minted": SECOND_COPILOT_PRODUCT_MINTED,
                "skills_grant": SKILLS_GRANT,
                "tab_writes": PRODUCT_SESSION_TAB_WRITES,
            }
        )

    def bind_identity(self, value: object) -> Result[str]:
        return parse_copilot_product_identity(value)

    def mint_second_copilot(self, value: object) -> Result[str]:
        return refuse_second_copilot_product(given=value)

    def treat_panel_as_copilot_product(self, panel_id: object) -> Result[object]:
        return refuse_panel_as_second_copilot(given=panel_id)

    def treat_engine_run_as_chat(self, session_id: object) -> Result[object]:
        return refuse_engine_run_as_chat(given=session_id)

    def open_home(
        self,
        *,
        product_session_id: object = "psess:home",
        principal: object = "operator",
        contribution: object | None = None,
        as_of: object = _DEFAULT_AS_OF,
        selected_refs: object = (),
        granted_ops: object = (),
    ) -> Result[ProductSession]:
        """Authoring home seat — independently scoped, instance optional."""
        return self.sessions.mint(
            product_session_id=product_session_id,
            profile=ProductSessionProfile.AUTHORING,
            principal=principal,
            contribution=dict(_DEFAULT_CONTRIBUTION) if contribution is None else contribution,
            instance_id=None,
            config_revision=4,
            as_of=as_of,
            granted_ops=granted_ops,
            selected_refs=selected_refs,
        )

    def open_app_use(
        self,
        *,
        product_session_id: object,
        instance_id: object,
        principal: object = "operator",
        contribution: object | None = None,
        as_of: object = _DEFAULT_AS_OF,
        granted_ops: object = (),
        selected_refs: object = (),
        panel_id: object | None = None,
        copilot_profile: object | None = ...,
    ) -> Result[ProductSession]:
        """App-use seat. Pack/profile and panel may be omitted."""
        if copilot_profile is not ... and copilot_profile is not None:
            parsed_profile = parse_wire_copilot_profile(copilot_profile)
            if is_refusal(parsed_profile):
                return parsed_profile
        minted = self.sessions.mint(
            product_session_id=product_session_id,
            profile=ProductSessionProfile.APP_USE,
            principal=principal,
            contribution=dict(_DEFAULT_CONTRIBUTION) if contribution is None else contribution,
            instance_id=instance_id,
            config_revision=4,
            as_of=as_of,
            granted_ops=granted_ops,
            selected_refs=selected_refs,
        )
        if is_refusal(minted):
            return minted
        if panel_id is None:
            return minted
        attached = self.chrome.open_tab(
            tab_id=panel_id,
            product_session_id=minted.value.product_session_id,
        )
        if is_refusal(attached):
            return attached
        return minted

    def omit_panel(self, product_session_id: object) -> Result[ProductSession]:
        """An instance may omit an in-app panel (DEC-0454; SCN-0024)."""
        loaded = self.sessions.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        if loaded.value.profile is not ProductSessionProfile.APP_USE:
            return policy_rejection(
                "panel",
                "omit-panel applies to an app-use instance seat",
                profile=loaded.value.profile.value,
            )
        return Ok(loaded.value)

    def note_published(self, qualified_id: str) -> None:
        self._published.add(qualified_id)

    def note_host_grant(self, qualified_id: str) -> None:
        self._host_grants.add(qualified_id)
        if self.listings is not None:
            self.listings.note_host_grant(qualified_id)

    def note_healthy(self, qualified_id: str) -> None:
        self._healthy.add(qualified_id)
        if self.listings is not None:
            self.listings.note_healthy(qualified_id)

    def tool_availability(self, product_session_id: object) -> Result[frozenset[str]]:
        """Published hits ∩ host grants ∩ session GrantRecords ∩ health."""
        loaded = self.sessions.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        records = self.sessions.granted_records(loaded.value.product_session_id)
        if is_refusal(records):
            return records
        session_ids = {row.contribution.qualified_id for row in records.value}
        published = set(self._published)
        host = set(self._host_grants)
        healthy = set(self._healthy)
        if self.listings is not None:
            listed = self.listings.list_contributions()
            if is_refusal(listed):
                return listed
            for row in listed.value:
                qid = row.hit.qualified_id
                if row.published:
                    published.add(qid)
                if row.granted:
                    host.add(qid)
                if row.healthy:
                    healthy.add(qid)
        return Ok(intersect_tool_availability(published, host, session_ids, healthy))

    def authorize_tool(
        self,
        product_session_id: object,
        qualified_id: object,
        *,
        hook_decision: HookResultDecision | str | None = None,
        skill: Skill | None = None,
        treat_hit_as_grant: bool = False,
        treat_skill_as_grant: bool = False,
    ) -> Result[str]:
        if not isinstance(qualified_id, str) or qualified_id.strip() == "":
            return invalid_input(
                "qualified_id",
                "tool availability names a non-empty qualified_id",
                given=repr(qualified_id),
            )
        token = qualified_id.strip()
        if skill is not None:
            described = refuse_skill_as_grant(skill, treat_as_grant=treat_skill_as_grant)
            if is_refusal(described):
                return described
        if treat_hit_as_grant:
            return refuse_hit_as_grant(qualified_id=token)
        available = self.tool_availability(product_session_id)
        if is_refusal(available):
            return available
        gated = privilege_gate_holds(
            available=available.value,
            qualified_id=token,
            hook_decision=hook_decision,
        )
        if is_refusal(gated):
            return gated
        return Ok(token)

    def nested_invoke(
        self,
        *,
        caller_product_session_id: object,
        callee_product_session_id: object,
        envelope: object,
        payload: object,
        now: object,
        contributions: Mapping[tuple[str, str], ContributionRecord] | None = None,
        descriptors: Mapping[tuple[str, int], OperationDescriptor] | None = None,
        instances: Mapping[tuple[str, int], InstanceRecord] | None = None,
        union_grants: bool = False,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundSessionGrant]:
        """Child runs under the callee instance's GrantRecords only."""
        return self.sessions.dispatch_public_call(
            callee_product_session_id,
            transport=PublicCallTransport.NESTED,
            envelope=envelope,
            payload=payload,
            now=now,
            contributions=contributions,
            descriptors=descriptors,
            instances=instances,
            execute=execute,
            caller_product_session_id=caller_product_session_id,
            union_grants=union_grants,
        )

    def retry_public_call(
        self,
        envelope: object,
        call: Callable[[InvocationEnvelope], Result[object]],
    ) -> Result[HostRetryResult]:
        """Host retries none/read flakes on the same logical_invocation_id."""
        return self.retry_loop.run(envelope, call)

    def submit_job(
        self,
        *,
        owner: ActorId | str,
        task_id: str,
        job_id: str | None = None,
    ) -> Result[JobHandle]:
        submitted = self.jobs.submit(owner=owner, task_id=task_id, job_id=job_id)
        if is_refusal(submitted):
            return submitted
        started = self.jobs.start(submitted.value.job_id)
        if is_refusal(started):
            return started
        return Ok(started.value)

    def dispose_panel(
        self,
        panel_id: object,
        *,
        product_session_id: object | None = None,
        job_id: object | None = None,
    ) -> Result[ProductSession]:
        """Dispose chrome. Running JobHandle is not cancelled (SCN-0024 Then 3)."""
        closed = self.chrome.close(panel_id, product_session_id=product_session_id)
        if is_refusal(closed):
            return closed
        if job_id is not None:
            if not isinstance(job_id, str) or job_id.strip() == "":
                return invalid_input("job_id", "job_id is a non-empty string", given=repr(job_id))
            detached = self.jobs.on_client_detach(job_id.strip(), event="tab_close")
            if is_refusal(detached):
                return detached
            if detached.value.state.value in {"cancelled", "aborted", "failed", "done"}:
                return policy_rejection(
                    "job_handle",
                    "disposing a panel must not cancel a running JobHandle (DEC-0454)",
                    state=detached.value.state.value,
                    cancels=PANEL_DISPOSE_CANCELS_JOB_HANDLE,
                )
        return closed

    def reconnect(
        self,
        product_session_id: object,
        *,
        resume_cursor: object,
        cursor_generation: object,
        **extra: object,
    ) -> Result[ReconnectSnapshot]:
        """Resume queries/events. Never replay unacked intent."""
        if extra:
            return refuse_reconnect_replays_intent(fields=sorted(extra))
        snapshot = self.sessions.reconnect(
            product_session_id,
            resume_cursor=resume_cursor,
            cursor_generation=cursor_generation,
        )
        if is_refusal(snapshot):
            return snapshot
        if snapshot.value.replays_unacked_intent:
            return refuse_reconnect_replays_intent(kind=snapshot.value.kind)
        return snapshot

    def transfer_context(
        self,
        *,
        kind: object,
        from_session: object,
        selected_refs: object | None = None,
        change_request: ChangeRequest | None = None,
    ) -> Result[ProductSession | ChangeRequest]:
        if not isinstance(kind, str) or kind not in CONTEXT_TRANSFER_KINDS:
            return refuse_context_transfer(kind)
        loaded = self.sessions.get(from_session)
        if is_refusal(loaded):
            return loaded
        if kind == "selected_refs":
            if selected_refs is None:
                return invalid_input(
                    "selected_refs",
                    "context transfer kind selected_refs requires selected_refs",
                )
            return Ok(loaded.value)
        if change_request is None:
            return invalid_input(
                "change_request",
                "context transfer kind change_request requires a ChangeRequest",
            )
        return Ok(change_request)

    def mint_change_request(
        self,
        *,
        from_session: object,
        change_request_id: object,
        targets: object,
        patch: object,
        copied_private_memory: object = False,
    ) -> Result[ChangeRequest]:
        """App-use mints. Does not apply."""
        loaded = self.sessions.get(from_session)
        if is_refusal(loaded):
            return loaded
        if loaded.value.profile is not ProductSessionProfile.APP_USE:
            return policy_rejection(
                "from_session",
                "app-use mints change_request; authoring plus operator principal applies",
                profile=loaded.value.profile.value,
                app_use_may_apply=APP_USE_MAY_APPLY,
            )
        return self.changes.mint(
            from_session=from_session,
            change_request_id=change_request_id,
            targets=targets,
            patch=patch,
            copied_private_memory=copied_private_memory,
        )

    def apply_change_request(
        self,
        *,
        change_request_id: object,
        from_session: object,
        operator_principal: object,
        applied_at: object,
    ) -> Result[ChangeApplyRecord]:
        """Story 58.4 remains the apply oracle. App-use cannot apply."""
        loaded = self.sessions.get(from_session)
        if is_refusal(loaded):
            return loaded
        if loaded.value.profile is ProductSessionProfile.APP_USE:
            return policy_rejection(
                "apply",
                "app-use may mint change_request and must not apply (DEC-0454; FR-PG-14)",
                profile=loaded.value.profile.value,
                applies=APP_USE_MAY_APPLY,
            )
        return self.changes.apply(
            change_request_id=change_request_id,
            authoring_session=from_session,
            operator_principal=operator_principal,
            applied_at=applied_at,
        )

    def write_package_source(self, *, from_session: object) -> Result[None]:
        return self.changes.write_package_source(from_session=from_session)

    def elevate_grants(self, *, from_session: object, grant_id: object) -> Result[None]:
        return self.changes.widen_grants(from_session=from_session, grant_id=grant_id)

    def retarget_account(
        self,
        *,
        from_session: object,
        account_scope: object,
    ) -> Result[None]:
        return self.changes.retarget_account(
            from_session=from_session,
            account_scope=account_scope,
        )

    def seat_for(self, session_id: object) -> Result[ProductSession]:
        if (
            isinstance(session_id, str)
            and session_id.startswith(ENGINE_RUN_ID_PREFIX)
            and not session_id.startswith(PRODUCT_SESSION_ID_PREFIX)
        ):
            return refuse_engine_run_as_chat(given=session_id)
        return self.sessions.get(session_id)

    def compare_seats(
        self,
        left_id: object,
        right_id: object,
    ) -> Result[Mapping[str, object]]:
        left = self.seat_for(left_id)
        if is_refusal(left):
            return left
        right = self.seat_for(right_id)
        if is_refusal(right):
            return right
        profiles = {left.value.profile.value, right.value.profile.value}
        if not profiles <= COPILOT_SEAT_PROFILES:
            return refuse_second_copilot_product(profiles=sorted(profiles))
        independent = left.value.product_session_id != right.value.product_session_id
        return Ok(
            MappingProxyType(
                {
                    "identity": COPILOT_PRODUCT_IDENTITY,
                    "independent": independent,
                    "left": left.value.product_session_id,
                    "right": right.value.product_session_id,
                    "seats": sorted(profiles),
                    "second_copilot": False,
                }
            )
        )


def hook_cannot_override(decision: HookResultDecision | str) -> Result[str]:
    """Failed privilege gates stay failed under an allow hook."""
    return refuse_hooks_override_privilege_gate(hook_decision=str(decision))
