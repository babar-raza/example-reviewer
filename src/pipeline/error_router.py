"""
Error Router for Risk-Based Routing (Track 2: D.4).

Implements the NEEDS_REVIEW workflow and risk-based error routing.
"""

import logging
from typing import List, Optional, Tuple
from ..core.models import ExampleRecord, ExampleStatus, ErrorRisk, FailureCategory, FailureDetail, FailureResolution
from ..core.database import Database
from ..services.telemetry_service import TelemetryService
from .risk_classifier import RiskClassifier

logger = logging.getLogger(__name__)


class ErrorRouter:
    """
    Routes errors based on risk classification.

    Implements:
    - Risk classification (LOW/MEDIUM/HIGH/CRITICAL)
    - Retry limit enforcement based on risk
    - Automatic escalation to NEEDS_REVIEW for high-risk errors
    - Telemetry emission for routing decisions
    """

    def __init__(
        self,
        db: Database,
        telemetry_service: Optional[TelemetryService] = None,
    ):
        """
        Initialize error router.

        Args:
            db: Database instance
            telemetry_service: Optional telemetry service for event emission
        """
        self.db = db
        self.telemetry_service = telemetry_service
        self.classifier = RiskClassifier()

    def route_compilation_error(
        self,
        example: ExampleRecord,
        error_messages: List[str],
        attempt_number: int,
        run_id: str,
        family: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Route compilation error based on risk level.

        Args:
            example: Example that failed
            error_messages: Compiler error messages
            attempt_number: Current attempt number (1-indexed)
            run_id: Pipeline run ID
            family: Product family

        Returns:
            Tuple of (should_continue_retries, escalation_reason)
            - should_continue_retries: False if should escalate to NEEDS_REVIEW
            - escalation_reason: Reason for escalation (if applicable)
        """
        # Classify risk
        risk = self.classifier.classify_compilation_error(error_messages)

        # Emit routing decision telemetry
        if self.telemetry_service:
            self.telemetry_service.emit_event(
                run_id=run_id,
                event_type='error_routing_decision',
                family=family,
                phase='compilation',
                example_id=example.example_id,
                metadata={
                    'risk_level': risk.value,
                    'attempt_number': attempt_number,
                    'error_count': len(error_messages),
                    'decision': 'escalate' if self.classifier.should_escalate_immediately(risk) else 'retry',
                }
            )

        # Check for immediate escalation (CRITICAL risk)
        if self.classifier.should_escalate_immediately(risk):
            escalation_reason = f"CRITICAL risk compilation error detected at attempt {attempt_number}"
            logger.warning(f"Escalating {example.example_id} to NEEDS_REVIEW: {escalation_reason}")

            # Emit escalation telemetry
            if self.telemetry_service:
                self.telemetry_service.emit_event(
                    run_id=run_id,
                    event_type='escalated_to_review',
                    family=family,
                    phase='compilation',
                    example_id=example.example_id,
                    success=False,
                    metadata={
                        'risk_level': risk.value,
                        'escalation_reason': escalation_reason,
                        'attempt_number': attempt_number,
                    }
                )

            # Save failure detail
            self._record_failure(
                run_id=run_id,
                example=example,
                phase='compilation',
                failure_category=FailureCategory.ESCALATED_TO_REVIEW,
                error_category='critical_compilation_error',
                error_message=f"Risk: {risk.value}. Errors: {'; '.join(error_messages[:3])}",
                resolution=FailureResolution.NEEDS_REVIEW,
            )

            return False, escalation_reason

        # Check retry limits based on risk
        max_retries = self.classifier.get_max_retries_for_risk(risk)

        if attempt_number > max_retries:
            escalation_reason = f"{risk.value} risk error exceeded max retries ({max_retries}) at attempt {attempt_number}"
            logger.info(f"Escalating {example.example_id} to NEEDS_REVIEW: {escalation_reason}")

            # Emit escalation telemetry
            if self.telemetry_service:
                self.telemetry_service.emit_event(
                    run_id=run_id,
                    event_type='escalated_to_review',
                    family=family,
                    phase='compilation',
                    example_id=example.example_id,
                    success=False,
                    metadata={
                        'risk_level': risk.value,
                        'escalation_reason': escalation_reason,
                        'attempt_number': attempt_number,
                        'max_retries': max_retries,
                    }
                )

            # Save failure detail
            self._record_failure(
                run_id=run_id,
                example=example,
                phase='compilation',
                failure_category=FailureCategory.ESCALATED_TO_REVIEW,
                error_category=f'{risk.value.lower()}_risk_retry_limit',
                error_message=f"Risk: {risk.value}. Attempt {attempt_number}/{max_retries}. Errors: {'; '.join(error_messages[:3])}",
                resolution=FailureResolution.NEEDS_REVIEW,
            )

            return False, escalation_reason

        # Continue retrying
        logger.debug(f"Allowing retry for {example.example_id}: risk={risk.value}, attempt={attempt_number}/{max_retries}")
        return True, None

    def route_runtime_error(
        self,
        example: ExampleRecord,
        exception_type: Optional[str],
        exception_message: Optional[str],
        stderr: Optional[str],
        attempt_number: int,
        run_id: str,
        family: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Route runtime error based on risk level.

        Args:
            example: Example that failed
            exception_type: Exception type name
            exception_message: Exception message
            stderr: Standard error output
            attempt_number: Current attempt number (1-indexed)
            run_id: Pipeline run ID
            family: Product family

        Returns:
            Tuple of (should_continue_retries, escalation_reason)
        """
        # Classify risk
        risk = self.classifier.classify_runtime_error(exception_type, exception_message, stderr)

        # Emit routing decision telemetry
        if self.telemetry_service:
            self.telemetry_service.emit_event(
                run_id=run_id,
                event_type='error_routing_decision',
                family=family,
                phase='runtime',
                example_id=example.example_id,
                metadata={
                    'risk_level': risk.value,
                    'attempt_number': attempt_number,
                    'exception_type': exception_type,
                    'decision': 'escalate' if self.classifier.should_escalate_immediately(risk) else 'retry',
                }
            )

        # Check for immediate escalation
        if self.classifier.should_escalate_immediately(risk):
            escalation_reason = f"CRITICAL risk runtime error detected at attempt {attempt_number}: {exception_type}"
            logger.warning(f"Escalating {example.example_id} to NEEDS_REVIEW: {escalation_reason}")

            # Emit escalation telemetry
            if self.telemetry_service:
                self.telemetry_service.emit_event(
                    run_id=run_id,
                    event_type='escalated_to_review',
                    family=family,
                    phase='runtime',
                    example_id=example.example_id,
                    success=False,
                    metadata={
                        'risk_level': risk.value,
                        'escalation_reason': escalation_reason,
                        'attempt_number': attempt_number,
                        'exception_type': exception_type,
                    }
                )

            # Save failure detail
            self._record_failure(
                run_id=run_id,
                example=example,
                phase='runtime',
                failure_category=FailureCategory.ESCALATED_TO_REVIEW,
                error_category='critical_runtime_error',
                error_message=f"Risk: {risk.value}. Exception: {exception_type}: {exception_message}",
                resolution=FailureResolution.NEEDS_REVIEW,
            )

            return False, escalation_reason

        # Check retry limits
        max_retries = self.classifier.get_max_retries_for_risk(risk)

        if attempt_number > max_retries:
            escalation_reason = f"{risk.value} risk error exceeded max retries ({max_retries}) at attempt {attempt_number}"
            logger.info(f"Escalating {example.example_id} to NEEDS_REVIEW: {escalation_reason}")

            # Emit escalation telemetry
            if self.telemetry_service:
                self.telemetry_service.emit_event(
                    run_id=run_id,
                    event_type='escalated_to_review',
                    family=family,
                    phase='runtime',
                    example_id=example.example_id,
                    success=False,
                    metadata={
                        'risk_level': risk.value,
                        'escalation_reason': escalation_reason,
                        'attempt_number': attempt_number,
                        'max_retries': max_retries,
                    }
                )

            # Save failure detail
            self._record_failure(
                run_id=run_id,
                example=example,
                phase='runtime',
                failure_category=FailureCategory.ESCALATED_TO_REVIEW,
                error_category=f'{risk.value.lower()}_risk_retry_limit',
                error_message=f"Risk: {risk.value}. Attempt {attempt_number}/{max_retries}. Exception: {exception_type}: {exception_message}",
                resolution=FailureResolution.NEEDS_REVIEW,
            )

            return False, escalation_reason

        # Continue retrying
        logger.debug(f"Allowing retry for {example.example_id}: risk={risk.value}, attempt={attempt_number}/{max_retries}")
        return True, None

    def escalate_to_review(
        self,
        example: ExampleRecord,
        escalation_reason: str,
        run_id: str,
        family: str,
        phase: str = 'unknown',
    ) -> None:
        """
        Escalate an example to NEEDS_REVIEW state.

        Args:
            example: Example to escalate
            escalation_reason: Reason for escalation
            run_id: Pipeline run ID
            family: Product family
            phase: Phase where escalation occurred
        """
        # Update example status
        example.status = ExampleStatus.NEEDS_REVIEW
        example.escalation_reason = escalation_reason
        self.db.save_example(example)

        logger.info(f"Escalated {example.example_id} to NEEDS_REVIEW: {escalation_reason}")

        # Emit telemetry
        if self.telemetry_service:
            self.telemetry_service.emit_event(
                run_id=run_id,
                event_type='escalated_to_review',
                family=family,
                phase=phase,
                example_id=example.example_id,
                success=False,
                metadata={
                    'escalation_reason': escalation_reason,
                }
            )

    def _record_failure(
        self,
        run_id: str,
        example: ExampleRecord,
        phase: str,
        failure_category: FailureCategory,
        error_category: str,
        error_message: str,
        resolution: FailureResolution,
    ) -> None:
        """
        Record failure detail in database.

        Args:
            run_id: Run ID
            example: Failed example
            phase: Phase where failure occurred
            failure_category: Category of failure
            error_category: Specific error type
            error_message: Error message
            resolution: Resolution status
        """
        failure = FailureDetail(
            run_id=run_id,
            example_id=example.example_id,
            phase=phase,
            failure_category=failure_category,
            error_category=error_category,
            error_message=error_message,
            resolution=resolution,
            metadata={
                'file_path': example.file_path,
                'block_index': example.location.block_index if example.location else 0,
            }
        )

        try:
            self.db.save_failure_detail(failure)
        except Exception as e:
            logger.warning(f"Failed to save failure detail: {e}")
