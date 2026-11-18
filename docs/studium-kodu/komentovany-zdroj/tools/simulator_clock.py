# Spoločný časový kontrakt aktuálneho simulátora. Experiment začína v UTC určenom scenárom pri t =
# 0; všetky uzly musia byť pripravené ešte pred vykonaním prvého kroku ns-3.
"""Shared experiment clock: SUMO, ns-3 and SNS-3 start at the selected UTC instant."""

EXPERIMENT_START_S = 0
SCHEMA_VERSION = 7
TIME_POLICY = 'ready_at_t0_full_duration'
