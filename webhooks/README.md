# Webhooks Codelab

This interactive codelab will teach you how to use a `WAIT_FOR_WEBHOOK` task to
resume an in-progress workflow after suspending its execution for up to 7 days.
It is an implementation of the concepts mentioned
[in this blog post from our CTO, Viren Baraiya](https://orkes.io/blog/late-bound-sagas-why-your-agent-is-not-an-llm-in-a-loop#what-it-looks-like-in-motion).

## Preparation

You will need to update the contents of `../settings.py` then confirm both
Python scripts included in this directory execute correctly before you can
start the codelab content.

<details>

<summary>Detailed instructions contained here</summary>

1. Review all configuration variables in `../settings.py` that have a comment
   beginning with "Replace" next to them. These need to be updated for your own
   account details.

2. After replacing `integration_name` and `llm_model` with your integration
   details, run `python -m webhooks.deploy_wait_for_webhook_workflow` from the
   top-level directory for all codelabs. This will deploy and run a workflow
   called "wait_for_webhook_demo" to your Orkes account that looks like this:

    <p align="center">
      <img
        src="images/wait_for_webhook_demo_workflow.png"
        alt="After running deploy_wait_for_webhook_demo_workflow.py, you should see a workflow similar to this in your Executions workflow tab. It will pause at the wait_for_webhook_ref task by design."
        height="300"
      >
    </p>

3. Before sending a webhook payload you will need to create a new webhook for
   your account. **Note that in the free developer version of Orkes Conductor
   you are only allowed to have one webhook defined.** Click on the following
   tab in the Orkes Conductor UI, click the "New webook" button in the top-right
   hand corner::

    <p align="center">
      <img
        src="images/create_new_webhook.png"
        alt="Where to find the Webhook tab and &quot;New webhook&quot; button in the Orkes Conductor UI."
        height="300"
      >
    </p>

4. Feel free to name your new webhook whatever you like. Note that it _must_
   have the `wait_for_webhook_demo` workflow selected in the "Workflows to
   receive webhook event" dropdown and the "Source platform" set to "Custom".
   Additionally, you _must_ add a header with a key entitled "source" and a
   descriptive value such as `wait-for-webhook-demo-value`; we'll be using it
   later for the webhook payload. It should look something like this before you
   click the "Save" button in the top-right hand corner of the page:

    <p align="center">
      <img
        src="images/new_webhook_configuration.png"
        alt="Sample webhook configuration, as described in step 4."
        height="300"
      >
    </p>

5. Before running the send_webhook_payload script, we need to update
   `settings.py` again with the details of our new webhook. Set `webhook_id` to
   the ID of your new webhook which can be found
   [in the configure-webhooks page of Orkes Conductor](https://developer.orkescloud.com/configure-webhooks).
   Set `source_header` to the value of the "source" header you entered in your
   webhook; I suggested `wait-for-webhook-demo-value` as an example. Finally,
   make sure you have at least one
   [Integration added to your Orkes account](https://developer.orkescloud.com/integrations?view=connections-and-resources) -
   change `integration_name` to the name of your desired integration, and
   `llm_model` to the specific model that this Integration uses.

6. Now run `python -m webhooks.send_webhook_payload` from the top level
   directory and keep an eye on the "wait_for_webhook_demo" execution from step
   2. If everything is configured correctly, you will receive a `200` status
   response from the send_webhook_payload script, your webhook will show a
   successful execution in the Orkes Conductor UI, and there will now be some
   output in the `llm_chat_complete` task:

    <p align="center">
      <img
        src="images/successful_webhook_execution.png"
        alt="A successful execution of the wait-for-webhook-demo webhook in the Orkes Conductor UI."
        height="300"
      >
    </p>

    <p align="center">
      <img
        src="images/successful_workflow_run.png"
        alt="A successful run of the wait_for_webhook_demo workflow in the Orkes Conductor UI, showing output in the llm_chat_complete task."
        height="300"
      >
    </p>

You are now ready to proceed with the exercises!

</details>

## Exercise 1: Increase Durability with Persistent Local Storage

Your goal for this exercise is to store the output from every completed
`send_email` task in a local database.

As noted in Viren's linked blog post, one of the big perks to this late-bound
saga architectural approach is we can write data from our tasks before the
`WAIT_FOR_WEBHOOK` to disk so we are no longer bound by our agentic runtime. We
can take this concept even further by storing data in a SQL database for
guaranteed ACID compliance and data integrity during the "suspended" portion of
our saga.

There are a wide variety of databases that you can use in projects, but for the
sake of simplicity in this codelab we're going to use a local
[sqlite3 database](https://docs.python.org/3/library/sqlite3.html) since this
comes built-in with python3. To create a new database called
"webhook_codelab_storage" run `python3 utils/create_sqlite_db.py` which creates
a new - also be sure to inspect this file to understand the schema of the
"emails" table.

To achieve this, update `utils/workers.py` so that each invocation of the
`send_email` worker returns the relevant information about its sent email. In
`deploy_wait_for_webhook_workflow.py`, retrieve the outputs from all completed
`send_email` task executions and insert one row per output into
`utils/webhook_codelab_storage.db`.

**Note: Although the starter workflow sends only one email, you will want keep
the retrieval and persistence logic collection-based so it continues to work in
future exercises!**

You can check that your code is writing data to the database correctly by using
the provided `utils/query_sqlite_db.py` helper file.

## Exercise 2: "Fan Out" by Scaling Email Inputs

Now that we have verified that we can durably store our email data in a local
database, we can expand on the workflow iteself. Currently we're only
processing a single email which isn't a particularly powerful or representative
use-case. For this exercise, your goal is to implement "the fan-out" part of the
saga in Viren's blog post; your workflow should accept multiple user IDs and
send an email to each user with parallel task executions.

Update the workflow and webhook payload to use a list of `user_ids` list instead of a single `user_id`, then resolve
all email addresses in one worker task. Next, use a
[`DynamicForkTask`](https://orkes.io/content/reference-docs/operators/dynamic-fork)
to create one uniquely referenced `send_email` task per recipient email address, followed by a
`JoinTask` before the existing `WAIT_FOR_WEBHOOK` task.
Your code from the Exercise 1 solution should store one database row for every
completed email task.

## Exercise 3: Multi-Turn Agentic Processing

(TODO)
