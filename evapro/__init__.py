"""Evapro - Automated add projects to annoeva Workflow Monitoring System
"""
from . import config, db, scripts
from annoeva.scripts.evaproject import main

__version__ = "0.1.2"
__author__ = "Zan Yuan <yfinddream@gmail.com>"
__license__ = "MIT"

__all__ = ["main", "config", "db", "scripts"]

