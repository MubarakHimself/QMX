# Handling credentials

This document explains how the system stores a password and rotates each API key.
No secret value is ever committed; a token is fetched at runtime through the secret
store. Talking *about* a password or a client secret in prose is not a leak and must
not be flagged.
