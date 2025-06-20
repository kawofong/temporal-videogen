# Temporal Videogen

A Temporal Workflow that generates video clips based on user prompt, powered by Google Gemini and Veo 2.

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

1. Start Temporal locally.

    ```bash
    temporal server start-dev
    ```

1. Run the workflow.

    ```bash
    uv run -m workflows.videogen.videogen
    ```
