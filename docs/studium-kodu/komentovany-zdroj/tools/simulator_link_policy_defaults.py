# Predvolené výskumné hodnoty RF, Dopplera a smerovania terminálu. V scenári ich možno explicitne
# nahradiť a verifier kontroluje, čo bolo odovzdané behu.
"""Published scenario defaults for the shared RSU satellite link envelope."""
LINK_POLICY = {
    'rf_hz': 29.5e9,
    'compensation': 0.98,
    'doppler_tolerance_hz': 20000.0,
    'zenith_cone_deg': 85.0,
    'steering_rate_deg_s': 90.0,
    'beam_half_angle_deg': 5.0,
}
