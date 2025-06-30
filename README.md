# Temporal Videogen

A Temporal Workflow that generates video clips based on user prompt, powered by Google Gemini and Veo 2.

https://github.com/user-attachments/assets/66ba8579-3cf0-495a-a98e-81df47e3623b

> This video is generated with the prompt `Mermaids, dolphins, and octopuses performing for a circus performance.`

## Pre-requisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [direnv](https://direnv.net/docs/installation.html)
- [Temporal CLI](https://docs.temporal.io/cli#install)
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk)

## Getting started

1. With this repository cloned, run the following at the root of the repository directory
to install Python dependencies:

    ```bash
    uv sync
    ```

1. Authenticate Google Cloud CLI.

    ```bash
    gcloud auth application-default login
    ```

    > Your Google Cloud credentials should be cached to your local file system.
    > Hence, you should not have to authenticate every time you are running this solution.

1. Copy `.envrc.example` and populate values:

    ```bash
    cp .envrc.example .envrc
    ```

1. Start Temporal locally.

    ```bash
    temporal server start-dev
    ```

1. In a new terminal, run the Worker.

    ```bash
    uv run poe run_worker
    ```

1. In a new terminal, run the Workflow.

    ```bash
    uv run poe run_workflow
    ```
