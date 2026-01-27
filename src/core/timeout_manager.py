"""
TimeoutManager for Example Reviewer Pipeline.

Provides cross-platform timeout enforcement at multiple levels:
1. LLM call timeout (ThreadPoolExecutor.result)
2. Code execution timeout (subprocess.run with timeout)
3. Per-example wall timeout (ThreadPoolExecutor.result)
4. Per-phase wall timeout (ThreadPoolExecutor.result)
5. Optional hard run timeout (external wrapper)

Windows-compatible: Uses subprocess.run(timeout=), asyncio.wait_for(),
and ThreadPoolExecutor.result(timeout=) instead of SIGALRM.
"""

import time
import logging
import asyncio
import subprocess
from typing import Callable, TypeVar, Optional, Any, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class TimeoutContext:
    """Context for a timeout operation."""
    operation_label: str
    timeout_seconds: int
    phase: Optional[str] = None
    example_key: Optional[str] = None
    run_id: Optional[str] = None
    family: Optional[str] = None


@dataclass
class TimeoutResult:
    """Result of a timeout-wrapped operation."""
    success: bool
    value: Any = None
    error: Optional[str] = None
    timed_out: bool = False
    duration_ms: int = 0


class TimeoutManager:
    """
    Cross-platform timeout enforcement manager.

    Provides timeout wrappers for various operation types:
    - Blocking functions (ThreadPoolExecutor)
    - Subprocess execution (subprocess.run with timeout)
    - Async operations (asyncio.wait_for)

    All timeout methods are Windows-compatible (no SIGALRM).
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize TimeoutManager.

        Args:
            max_workers: Maximum thread pool workers for blocking operations
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_operations: Dict[str, TimeoutContext] = {}

    def execute_with_timeout(
        self,
        func: Callable[[], T],
        context: TimeoutContext,
        on_timeout: Optional[Callable[[TimeoutContext], None]] = None,
    ) -> TimeoutResult:
        """
        Execute a blocking function with timeout enforcement.

        Uses ThreadPoolExecutor.result(timeout=) for cross-platform compatibility.

        Args:
            func: Callable to execute
            context: Timeout context with operation metadata
            on_timeout: Optional callback invoked when timeout occurs

        Returns:
            TimeoutResult with execution outcome
        """
        start_time = time.time()
        operation_id = f"{context.operation_label}_{id(func)}"
        self._active_operations[operation_id] = context

        try:
            logger.debug(
                f"Starting operation '{context.operation_label}' "
                f"with timeout={context.timeout_seconds}s"
            )

            future = self._executor.submit(func)

            try:
                result = future.result(timeout=context.timeout_seconds)
                duration_ms = int((time.time() - start_time) * 1000)

                logger.debug(
                    f"Operation '{context.operation_label}' completed "
                    f"in {duration_ms}ms"
                )

                return TimeoutResult(
                    success=True,
                    value=result,
                    duration_ms=duration_ms,
                    timed_out=False,
                )

            except FutureTimeoutError:
                duration_ms = int((time.time() - start_time) * 1000)

                logger.error(
                    f"Timeout exceeded: operation '{context.operation_label}' "
                    f"exceeded {context.timeout_seconds}s "
                    f"(phase={context.phase}, example_key={context.example_key})"
                )

                # Invoke timeout callback if provided
                if on_timeout:
                    try:
                        on_timeout(context)
                    except Exception as e:
                        logger.warning(f"Timeout callback failed: {e}")

                # Cancel the future (best effort)
                future.cancel()

                return TimeoutResult(
                    success=False,
                    error=f"Operation timeout after {context.timeout_seconds}s",
                    timed_out=True,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Operation '{context.operation_label}' failed: {e}")

            return TimeoutResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )

        finally:
            self._active_operations.pop(operation_id, None)

    def execute_subprocess_with_timeout(
        self,
        args: list,
        context: TimeoutContext,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        text: bool = True,
        on_timeout: Optional[Callable[[TimeoutContext], None]] = None,
    ) -> TimeoutResult:
        """
        Execute subprocess with timeout.

        Uses subprocess.run(timeout=) for cross-platform compatibility.

        Args:
            args: Command arguments list
            context: Timeout context
            cwd: Working directory
            env: Environment variables
            capture_output: Capture stdout/stderr
            text: Use text mode
            on_timeout: Optional callback invoked on timeout

        Returns:
            TimeoutResult with subprocess result
        """
        start_time = time.time()

        logger.debug(
            f"Executing subprocess '{context.operation_label}': {' '.join(args[:3])}... "
            f"(timeout={context.timeout_seconds}s)"
        )

        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=capture_output,
                text=text,
                timeout=context.timeout_seconds,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(
                f"Subprocess '{context.operation_label}' completed "
                f"with exit_code={result.returncode} in {duration_ms}ms"
            )

            return TimeoutResult(
                success=(result.returncode == 0),
                value=result,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"Subprocess timeout: '{context.operation_label}' "
                f"exceeded {context.timeout_seconds}s "
                f"(phase={context.phase}, example_key={context.example_key})"
            )

            # Invoke timeout callback
            if on_timeout:
                try:
                    on_timeout(context)
                except Exception as callback_error:
                    logger.warning(f"Timeout callback failed: {callback_error}")

            # Return timeout result with partial output if available
            return TimeoutResult(
                success=False,
                value={
                    'stdout': e.stdout.decode() if e.stdout and isinstance(e.stdout, bytes) else str(e.stdout or ''),
                    'stderr': e.stderr.decode() if e.stderr and isinstance(e.stderr, bytes) else str(e.stderr or ''),
                    'timeout': context.timeout_seconds,
                },
                error=f"Subprocess timeout after {context.timeout_seconds}s",
                timed_out=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Subprocess '{context.operation_label}' failed: {e}")

            return TimeoutResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )

    async def execute_async_with_timeout(
        self,
        coro,
        context: TimeoutContext,
        on_timeout: Optional[Callable[[TimeoutContext], None]] = None,
    ) -> TimeoutResult:
        """
        Execute async operation with timeout.

        Uses asyncio.wait_for() for cross-platform compatibility.

        Args:
            coro: Coroutine to execute
            context: Timeout context
            on_timeout: Optional callback invoked on timeout

        Returns:
            TimeoutResult with execution outcome
        """
        start_time = time.time()

        logger.debug(
            f"Executing async operation '{context.operation_label}' "
            f"with timeout={context.timeout_seconds}s"
        )

        try:
            result = await asyncio.wait_for(coro, timeout=context.timeout_seconds)
            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(
                f"Async operation '{context.operation_label}' completed "
                f"in {duration_ms}ms"
            )

            return TimeoutResult(
                success=True,
                value=result,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"Async timeout: operation '{context.operation_label}' "
                f"exceeded {context.timeout_seconds}s "
                f"(phase={context.phase}, example_key={context.example_key})"
            )

            # Invoke timeout callback
            if on_timeout:
                try:
                    on_timeout(context)
                except Exception as e:
                    logger.warning(f"Timeout callback failed: {e}")

            return TimeoutResult(
                success=False,
                error=f"Async operation timeout after {context.timeout_seconds}s",
                timed_out=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Async operation '{context.operation_label}' failed: {e}")

            return TimeoutResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )

    def get_active_operations(self) -> Dict[str, TimeoutContext]:
        """
        Get all currently active timeout-wrapped operations.

        Returns:
            Dictionary of operation_id -> TimeoutContext
        """
        return dict(self._active_operations)

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Shutdown the timeout manager.

        Args:
            wait: Wait for active operations to complete
            timeout: Maximum time to wait for shutdown
        """
        logger.info("Shutting down TimeoutManager...")

        if wait and self._active_operations:
            logger.info(
                f"Waiting for {len(self._active_operations)} active operations..."
            )

        self._executor.shutdown(wait=wait, cancel_futures=not wait)
        logger.info("TimeoutManager shutdown complete")


def create_timeout_callback(
    db,
    telemetry_service,
    emit_telemetry: bool = True,
    insert_failure_details: bool = True,
    mark_terminal_state: bool = True,
) -> Callable[[TimeoutContext], None]:
    """
    Create a timeout callback that handles telemetry and database updates.

    Args:
        db: Database instance
        telemetry_service: TelemetryService instance (or None)
        emit_telemetry: Emit timeout_exceeded telemetry event
        insert_failure_details: Insert failure_details row
        mark_terminal_state: Mark example as failed terminal state

    Returns:
        Callback function for timeout events
    """
    def on_timeout(context: TimeoutContext):
        """Handle timeout event."""
        try:
            # 1. Emit telemetry event
            if emit_telemetry and telemetry_service:
                try:
                    telemetry_service.emit_event(
                        run_id=context.run_id,
                        event_type='timeout_exceeded',
                        family=context.family,
                        phase=context.phase,
                        example_id=context.example_key,
                        metadata={
                            'operation': context.operation_label,
                            'timeout_seconds': context.timeout_seconds,
                            'phase': context.phase,
                            'example_key': context.example_key,
                        },
                        success=False,
                    )
                    logger.debug(f"Emitted timeout_exceeded telemetry for {context.operation_label}")
                except Exception as e:
                    logger.warning(f"Failed to emit timeout telemetry: {e}")

            # 2. Insert failure_details row
            if insert_failure_details and context.example_key and context.run_id:
                try:
                    from ..pipeline.failure_tracker import track_timeout_failure
                    track_timeout_failure(
                        db=db,
                        run_id=context.run_id,
                        phase=context.phase,
                        example_id=context.example_key,
                        timeout_seconds=context.timeout_seconds,
                        context=context.operation_label,
                    )
                    logger.debug(f"Inserted failure_details for timeout: {context.example_key}")
                except Exception as e:
                    logger.warning(f"Failed to insert failure_details: {e}")

            # 3. Mark example in terminal state
            if mark_terminal_state and context.example_key:
                try:
                    db.update_example_status(
                        example_id=context.example_key,
                        status='FAILED',
                        failure_reason=f"Timeout: {context.operation_label} exceeded {context.timeout_seconds}s",
                    )
                    logger.debug(f"Marked example as FAILED due to timeout: {context.example_key}")
                except Exception as e:
                    logger.warning(f"Failed to mark example as failed: {e}")

        except Exception as e:
            logger.error(f"Timeout callback failed catastrophically: {e}")

    return on_timeout
