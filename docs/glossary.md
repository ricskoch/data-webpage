# Glossary

Plain-language terms. The agent adds a term here whenever it introduces one.

- **CI (continuous integration):** automatic checks that run on every change before it can be merged.
- **PR (pull request):** a proposed change that you review before it joins the main code.
- **Branch protection:** a GitHub setting that stops anyone, including you by accident, from pushing straight to `main`.
- **Preview deployment:** a temporary copy of the site for one PR, so you can click through before it goes live.
- **CDN:** servers around the world that hold copies of the site so it loads quickly.
- **Object storage (R2):** a place for large files. Not a database.
- **Parquet:** a compact file format for tables that lets a program read only the columns and rows it needs.
- **Range request:** asking a server for just part of a file. This lets the browser read a small slice of a large Parquet file.
- **DuckDB-Wasm:** a database engine that runs inside the browser tab.
- **CORS:** a browser safety rule about which sites may read which files. Needs configuring for data files.
- **Manifest:** a small JSON file describing a dataset version: schema, row counts, checksums, licence.
- **Checksum (SHA-256):** a fingerprint of a file. If one bit changes, the fingerprint changes.
- **Screen (CRISPR):** one experiment that perturbs many genes and measures an effect.
- **Rank-based comparison:** comparing screens by gene order rather than raw score, because score scales differ.
