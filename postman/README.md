# API Postman Collection

This directory contains the Postman Collection and Environment files for the **chatbox** API.

## Getting Started

To use these files in your local Postman app, follow these steps:

### 1. Import the Collection

1. Open **Postman**.
2. Click the **Import** button in the top-left sidebar (or press `Ctrl+O` / `Cmd+O`).
3. Drag and drop the `collection.json` file from this folder into the import window.
4. Click **Import** to confirm.

### 2. Import the Environment

1. Click the **Import** button again.
2. Drag and drop the `environment.json` file.
3. Once imported, go to the top-right corner of Postman and select the newly imported environment from the dropdown menu (it may be named "Development" or "Staging").

### 3. Set Your Secrets (Required)

For security reasons, sensitive credentials (API Keys, Tokens, Passwords) are **not** included in the exported files.

1. Click the **Environments** tab on the left sidebar.
2. Select the environment you just imported.
3. In the **Current Value** column, paste your personal API keys or tokens for the following variables:
   - `api_key`
   - `client_secret`
   - [Add any other specific variables here]
4. Click **Save**.

---

## Maintenance

If you make changes to the API routes:

1. Right-click the collection in Postman and select **Export**.
2. Overwrite the `collection.json` file in this repository.
3. Commit and push your changes to GitHub.
