"""Single append-only journal, journal_seq, announcement law (AD-6).

Durable journal appends go through
:class:`~qma.daemon.persistence.PersistenceSubstrate` (FR-Q22 sole-writer
boundary); this module owns journal_seq allocation and the announcement law
in later stories.
"""
