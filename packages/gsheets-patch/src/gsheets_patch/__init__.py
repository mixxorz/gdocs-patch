"""Thin access to selected Google Sheets v4 methods."""

from gsheets_patch.client import GoogleSheetsClient
from gsheets_patch.schema import METHODS, describe_schema

__all__ = ["METHODS", "GoogleSheetsClient", "describe_schema"]
