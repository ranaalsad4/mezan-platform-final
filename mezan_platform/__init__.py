"""Mezan platform service layer (app v3).

Thin, Streamlit-free functions that call the unchanged model v1.3 engines in `carbon_iq` and return plain
dictionaries for the interface, the AI explanation layer and the report exporter. No equation of the model lives here;
the only new quantitative helpers are a bisection refinement of existing switch-point sweeps and a discount-rate sweep
of the existing decision rule (both documented in docs/METHODS_V3.md).
"""
APP_NAME = "MEZAN | ميزان"
APP_TAGLINE = "AI-Assisted Industrial Investment Platform"
APP_VERSION = "3.1"
