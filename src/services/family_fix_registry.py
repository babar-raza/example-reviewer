"""
Generic registry for family-specific runtime fix functions.

Architecture (P2 compliance):
- Generic: this file defines the registry interface and dispatch mechanism
- Family-specific: fix implementations live in src/services/family_fixes/<family>_fixes.py

Each fix function signature:
    def fix_fn(code: str, error_text: str) -> Optional[Tuple[str, str]]:
        \"\"\"Returns (fixed_code, description) or None if fix does not apply.\"\"\"

Catalog dependency: each fix function must only use API types confirmed to exist
in the family API catalog (P1 compliance).
"""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Registry: family name -> list of runtime fix callables
# Populated by family fix modules on import (see family_fixes/ directory)
_RUNTIME_FIX_REGISTRY: Dict[str, List[Callable]] = {}


def register_runtime_fix(family: str, fix_fn: Callable) -> None:
    """Register a family-specific runtime fix function."""
    if family not in _RUNTIME_FIX_REGISTRY:
        _RUNTIME_FIX_REGISTRY[family] = []
    _RUNTIME_FIX_REGISTRY[family].append(fix_fn)
    logger.debug(f"Registered runtime fix '{fix_fn.__name__}' for family '{family}'")


def get_runtime_fixes(family: str) -> List[Callable]:
    """Get all registered runtime fix functions for a family."""
    # Ensure family modules are loaded (lazy import)
    _ensure_family_loaded(family)
    return _RUNTIME_FIX_REGISTRY.get(family, [])


def apply_family_runtime_fixes(
    family: str,
    code: str,
    error_text: str,
) -> Optional[Tuple[str, str]]:
    """
    Apply family-specific runtime fixes to code.

    Tries each registered fix in order. Returns (fixed_code, description)
    from the first fix that applies, or None if no fix applies.

    Args:
        family: Family name (e.g. 'words', 'zip')
        code: Current code to fix
        error_text: Full runtime error output

    Returns:
        Tuple of (fixed_code, description) or None
    """
    fixes = get_runtime_fixes(family)
    if not fixes:
        return None

    for fix_fn in fixes:
        try:
            result = fix_fn(code, error_text)
            if result is not None:
                fixed_code, desc = result
                logger.info(f"Family runtime fix applied [{family}]: {desc}")
                return fixed_code, desc
        except Exception as e:
            logger.warning(f"Family runtime fix '{fix_fn.__name__}' failed: {e}")
            continue

    return None


# Behavioral fix registry: family name -> list of proactive fix callables
# Signature: def fix_fn(code: str) -> Optional[Tuple[str, str]]
_BEHAVIORAL_FIX_REGISTRY: Dict[str, List[Callable]] = {}


def register_behavioral_fix(family: str, fix_fn: Callable) -> None:
    """Register a family-specific behavioral (proactive) fix function.

    Unlike runtime fixes, behavioral fixes receive only the code (no error_text)
    and are called after the behavioral scanner detects a blocking pattern.
    """
    if family not in _BEHAVIORAL_FIX_REGISTRY:
        _BEHAVIORAL_FIX_REGISTRY[family] = []
    _BEHAVIORAL_FIX_REGISTRY[family].append(fix_fn)
    logger.debug(f"Registered behavioral fix '{fix_fn.__name__}' for family '{family}'")


def apply_family_behavioral_fixes(family: str, code: str) -> Optional[Tuple[str, str]]:
    """Apply family-specific behavioral fixes to code.

    Tries each registered behavioral fix in order. Returns (fixed_code, description)
    from the first fix that applies, or None if no fix applies.
    """
    _ensure_family_loaded(family)
    fixes = _BEHAVIORAL_FIX_REGISTRY.get(family, [])
    for fix_fn in fixes:
        try:
            result = fix_fn(code)
            if result is not None:
                fixed_code, desc = result
                logger.info(f"Family behavioral fix applied [{family}]: {desc}")
                return fixed_code, desc
        except Exception as e:
            logger.warning(f"Family behavioral fix '{fix_fn.__name__}' failed: {e}")
    return None


# Harness registry: family name -> callable(body, extra_usings, data_dir) -> str
_HARNESS_REGISTRY: Dict[str, Callable] = {}


def register_synthesis_harness(family: str, harness_fn: Callable) -> None:
    """Register a family-specific synthesis harness function."""
    _HARNESS_REGISTRY[family] = harness_fn
    logger.debug(f"Registered synthesis harness for family '{family}'")


def get_synthesis_harness(family: str, body: str, extra_usings: str = "", data_dir: str = ".") -> Optional[str]:
    """
    Return a testable harness wrapping extracted product API calls.

    Dispatches to the family-specific harness function if registered.
    Returns None if no harness is registered for the family.
    """
    _ensure_family_loaded(family)
    fn = _HARNESS_REGISTRY.get(family)
    if fn is None:
        return None
    try:
        return fn(body=body, extra_usings=extra_usings, data_dir=data_dir)
    except Exception as e:
        logger.warning(f"Synthesis harness for '{family}' raised: {e}")
        return None


# Lazy family module loader
_LOADED_FAMILIES: set = set()

def _ensure_family_loaded(family: str) -> None:
    """Lazy-load the fix module for a family on first access."""
    if family in _LOADED_FAMILIES:
        return
    _LOADED_FAMILIES.add(family)
    try:
        import importlib
        module_name = f"src.services.family_fixes.{family}_fixes"
        importlib.import_module(module_name)
        logger.debug(f"Loaded family fix module: {module_name}")
    except ModuleNotFoundError:
        # No fix module for this family -- that's fine
        logger.debug(f"No family fix module for '{family}' (src.services.family_fixes.{family}_fixes)")
    except Exception as e:
        logger.warning(f"Failed to load family fix module for '{family}': {e}")
