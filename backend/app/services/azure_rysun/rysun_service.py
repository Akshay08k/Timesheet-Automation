"""Compatibility module for MyCompany Azure DevOps connector."""

from backend.app.services.azure_mycompany.mycompany_service import (
    AzureMyCompanyService,
    AzureRysunService,
)

__all__ = ["AzureMyCompanyService", "AzureRysunService"]
