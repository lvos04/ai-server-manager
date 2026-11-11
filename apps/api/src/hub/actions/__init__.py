"""Acties en goedkeuringen in de Hub (B01-007, B01-003; contract 1.3 §8, ADR-0030).

Stroom: voorstel → deterministische classificatie (:mod:`asm_policy`) → preview met hash + ETag van het doel uit een
eigen alleen-lezen readback → bij R2/R3 een gebonden goedkeuring van een beheerder → ondertekend ``ExecutionRequest``
naar de executor, die alles zelf opnieuw controleert. De Hub schrijft zelf nooit naar TrueNAS.
"""
