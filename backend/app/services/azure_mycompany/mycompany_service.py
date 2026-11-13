"""Compatibility module for Azure Rysun connector."""

from backend.app.services.azure_rysun.rysun_service import (
    AzureRysunService,
    AzureMyCompanyService,
)

__all__ = ["AzureRysunService", "AzureMyCompanyService"]
