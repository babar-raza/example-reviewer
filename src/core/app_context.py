"""
Application context types for C# code examples.

This module defines the application architecture context of code snippets
to enable context-aware validation and substitution.
"""

from enum import Enum


class AppContext(str, Enum):
    """
    Application context type for C# code examples.

    Used to distinguish between different application architectures to prevent
    incorrect cross-context substitution (e.g., ASP.NET minimal API → console).
    """

    CONSOLE = "console"
    """Traditional console application with Main() entrypoint."""

    ASPNET_CORE_MINIMAL = "aspnet_core_minimal"
    """ASP.NET Core minimal hosting API (WebApplication.CreateBuilder)."""

    ASPNET_CORE_MVC = "aspnet_core_mvc"
    """ASP.NET Core MVC (Controller-based with Views)."""

    ASPNET_CORE_WEBAPI = "aspnet_core_webapi"
    """ASP.NET Core Web API (ApiController-based)."""

    LIBRARY = "library"
    """Class library with no entrypoint."""

    UNKNOWN = "unknown"
    """Could not determine context."""
