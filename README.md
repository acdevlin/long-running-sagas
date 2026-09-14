# Long Running Sagas

Experimental directory for agentic processes that take along time (eg: on the order of days, at minimum) to execute.

Be sure to [create a virtual environment](https://docs.python.org/3/library/venv.html), activate it, then `pip install -r requirements.txt` to install important dependencies before trying any of these codelabs!

## Webhooks

This interactive codelab will teach you how to use a `WAIT_FOR_WEBHOOK` task to resume an in-progress workflow after suspending its execution for up to 7 days. It is an implementation of the concepts mentioned [in this blog post from our CTO, Viren Baraiya](https://orkes.io/blog/late-bound-sagas-why-your-agent-is-not-an-llm-in-a-loop#what-it-looks-like-in-motion).

To run the provided code, perform the following steps after cloning this repository and changing the contents of `settings.py` for your own account details:

1. `python -m webhooks.deploy_wait_for_webhook_workflow`
1. Wait for the resulting workflow to reach the "wait_for_webhook_ref" task.
1. In another terminal, run `python -m webhooks.serve_webhook_agent` and leave
   it running to serve the agent's local database tools.
1. Back in your first terminal: run `python -m webhooks.send_webhook_payload`
