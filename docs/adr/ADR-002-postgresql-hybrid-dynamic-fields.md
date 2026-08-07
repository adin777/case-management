# ADR-002: PostgreSQL hybrid dynamic fields

Status: Accepted. Stable case attributes use columns; dynamic values use one typed row per field. JSON is reserved for field configuration and exceptional structured values, avoiding opaque case blobs.
