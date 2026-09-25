# Webhooks Codelab

This interactive codelab will teach you how to use a
[`WAIT_FOR_WEBHOOK` task](https://orkes.io/content/reference-docs/system-tasks/wait-for-webhook)
to resume an in-progress workflow after suspending its execution for up to 7
days. It is an implementation of the concepts mentioned
[in this blog post from our CTO, Viren Baraiya](https://orkes.io/blog/late-bound-sagas-why-your-agent-is-not-an-llm-in-a-loop#what-it-looks-like-in-motion).
By the end of this codelab, you will have built a durable email-processing
pipeline that sends emails in parallel, stores their receipts in a local
database, and pauses until an external webhook resumes the workflow. A
multi-turn agent will then analyze the stored email activity and produce a
concise digest.

## Choose a Language

This codelab is available in the following languages. Each version has the
same exercises, and its README explains how to set it up, how to run each step,
and where to find each part of the code:

- [Python](python/README.md)
- [C#](csharp/README.md)

Every language version provides the same five steps, which this README refers
to by name:

| Step | What it does |
| --- | --- |
| **create-db** | Creates the local database used from Exercise 1 onward |
| **deploy-workflow** | Registers the agent and workflow, starts an execution, and exits once it reaches the `WAIT_FOR_WEBHOOK` task |
| **serve-agent** | Runs the agent's local tool workers until you stop it |
| **send-webhook** | Sends the webhook payload that resumes the workflow |
| **query-db** | Prints the emails stored in the local database |

Each language version registers its own workflow and agent, named after the
language (for example `wait_for_webhook_demo_python` and
`webhook_customer_service_python`), so you can tell their runs apart in the
Orkes Conductor UI. All language versions share one webhook, and each
language's **send-webhook** step only resumes that language's workflow.

The language versions do share task names such as `send_email`, and Conductor
gives each task to whichever worker asks for it first. If you work through more
than one language, run only one language's steps at a time, and stop any
**serve-agent** process from another language before you start.

## Preparation

Complete the [Setup section of the top-level README](../README.md#setup) and
the setup steps for your chosen language first so the Conductor SDK can
authenticate with your account. You will then need to add a few more values to
`.env` and confirm that the **deploy-workflow**, **serve-agent** and
**send-webhook** steps run correctly before you can start the codelab content.

<details>

<summary>Detailed instructions contained here</summary>

The screenshots in these steps come from the Python version of the codelab, so
they show names such as `wait_for_webhook_demo_python` and
`webhook_customer_service_python`. The steps are the same for every language
version; your workflow and agent names end with your own language's name
instead, as listed in your language's README.

1. Open the `.env` file you created at the top level of this repository. The
   values in its "Agent LLM" and "Webhooks codelab" sections need to be updated
   for your own account details.

2. Make sure you have at least one
   [Integration added to your Orkes account](https://developer.orkescloud.com/integrations?view=connections-and-resources),
   then set `CONDUCTOR_INTEGRATION_NAME` to the name of that integration and
   `CONDUCTOR_AGENT_LLM_MODEL` to the specific model it uses. Now run the
   **deploy-workflow** step. This will deploy and run a workflow named after
   your language, such as "wait_for_webhook_demo_python", to your Orkes account
   that looks like this:

    <p align="center">
      <img
        src="images/wait_for_webhook_demo_workflow.png"
        alt="After running the deploy-workflow step, you should see a workflow similar to this in your Executions workflow tab. It will pause at the wait_for_webhook_ref task by design."
        height="300"
      >
    </p>

3. Before sending a webhook payload, follow the
   [webhook integration guide](https://orkes.io/content/developer-guides/webhook-integration)
   to create a new webhook for your account. **Note that in the free developer
   version of Orkes Conductor you are only allowed to have one webhook defined.**
   If you already created the webhook for another language version of this
   codelab, don't create a second one: open it from the Webhook tab, add your
   language's workflow from step 2 to its "Workflows to receive webhook event"
   dropdown, click "Save", and continue from step 5. Otherwise, click on the
   Webhook tab in the Orkes Conductor UI, then click the "New webhook" button in
   the top-right hand corner:

    <p align="center">
      <img
        src="images/create_new_webhook.png"
        alt="Where to find the Webhook tab and &quot;New webhook&quot; button in the Orkes Conductor UI."
        height="300"
      >
    </p>

4. Feel free to name your new webhook whatever you like. Note that it _must_
   have your language's workflow from step 2, such as
   `wait_for_webhook_demo_python`, selected in the "Workflows to receive webhook
   event" dropdown (select one for each language you plan to use), and the
   "Source platform" set to "Custom".
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

5. Before running the **send-webhook** step, we need to update `.env` again
   with the details of our new webhook. Set `WEBHOOK_ID` to the ID of your new
   webhook which can be found
   [in the configure-webhooks page of Orkes Conductor](https://developer.orkescloud.com/configure-webhooks).
   Set `WEBHOOK_SOURCE_HEADER` to the value of the "source" header you entered
   in your webhook; I suggest `wait-for-webhook-demo-value` as an example.

6. After the **deploy-workflow** step reports that `wait_for_webhook_ref` is
   ready, run the **serve-agent** step in another terminal. Leave this
   process running so it can serve the agent's local database tools after the
   workflow resumes.

7. Now run the **send-webhook** step and keep an eye on the workflow
   execution from step 2. If everything is configured
   correctly, you will receive a `200` status response from the
   **send-webhook** step, your webhook will show a
   successful execution in the Orkes Conductor UI, and there will now be some
   output in the `invoke_agent` task. After the workflow completes, stop
   the agent tool worker process with Ctrl+C.

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
        alt="A successful run of the codelab's workflow in the Orkes Conductor UI, showing output in the invoke_agent task."
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
[SQLite database](https://sqlite.org/) since it is stored in a single file and
needs no database server. To create a new database called
"webhook_codelab_storage", run the **create-db** step. Be sure to inspect
[shared/schema.sql](shared/schema.sql) to understand the schema of the "emails"
table.

To write our data to disk, update the `send_email` worker so that each
invocation returns the relevant information about its sent email. In the
**deploy-workflow** step's code, retrieve the outputs from all completed
`send_email` task executions and insert one row per output into the
"webhook_codelab_storage" database.

**Note: Although the starter workflow sends only one email, you will want to
keep the retrieval and persistence logic collection-based so it continues to
work in future exercises!**

You can check that your code is writing data to the database correctly by
running the **query-db** step.

## Exercise 2: "Fan Out" by Scaling Email Inputs

Now that we have verified that we can durably store our email data in a local
database, we can expand on the workflow itself. Currently we're only
processing a single email which isn't a particularly powerful or representative
use case. For this exercise, your goal is to implement "the fan-out" part of the
saga in Viren's blog post; your workflow should accept multiple user IDs and
send an email to each user with parallel task executions.

Update the workflow and webhook payload to use a list of `user_ids` instead of a
single `user_id`, then resolve all email addresses in one worker task. Next, use
a [`DYNAMIC_FORK` task](https://orkes.io/content/reference-docs/operators/dynamic-fork)
to create one uniquely referenced `send_email` task per recipient email
address, followed by a `JOIN` task before the existing `WAIT_FOR_WEBHOOK` task.
Your code from the Exercise 1 solution should store one database row for every
completed email task.

## Exercise 3: Multi-Turn Agentic Processing

We have now scaled up the email inputs to our persistent pipeline. Now it's
time to update the agent downstream from the `WAIT_FOR_WEBHOOK` task, since it
currently doesn't do anything meaningful with the email data.

In this exercise, give your language's agent, such as
`webhook_customer_service_python`, two new tools:

1. `summarize_email_activity`, which returns the total number of stored emails
   and the number sent to each recipient.
2. `get_recipient_email_history`, which returns the detailed records for one
   recipient.

Implement both functions as read-only agent tools (your language's README
explains how its SDK declares a tool), then add them to the agent's tool list.
Have the agent first review the summary, and, if no stored activity exists,
return a concise no-activity digest. Otherwise, have it identify the recipient
with the greatest number of stored emails, retrieve that recipient's history,
and then write a concise activity digest.

You will also need to update the webhook's `agent_input` to request this
analysis. After the workflow reaches `WAIT_FOR_WEBHOOK` and the
**deploy-workflow** step exits, run the **serve-agent** step in another
terminal. Keep this separate process running while you send the webhook so the
resumed workflow can execute the agent's local database tools. If
**serve-agent** is still running from an earlier run, stop it and run it again:
it keeps running the code it started with, so it won't have your new tools.

As part of your verification with a non-empty database, confirm that the
Conductor execution contains two dependent tool calls followed by the final
digest. With an empty database, confirm that the summary call is followed
directly by the no-activity digest.

## Recap: What You Built

By completing this codelab, you built a durable, event-driven email workflow
that:

- Resolves multiple user IDs in one `get_user_emails` task, then uses a
  `DYNAMIC_FORK` and `JOIN` to send the emails in parallel.
- Collects every completed `send_email` result and stores the records in a local
  database while the workflow is suspended.
- Uses `WAIT_FOR_WEBHOOK` to pause without consuming worker resources, then
  resumes when a matching external event arrives.
- Hands the durable email history to a multi-turn agent that summarizes the
  overall email activity.

This demonstrates the central idea from
[Late-Bound Sagas: Why Your Agent Is Not an LLM in a Loop](https://orkes.io/blog/late-bound-sagas-why-your-agent-is-not-an-llm-in-a-loop):
Conductor owns the execution state across task and process boundaries, while
workers perform concrete actions and the LLM decides what information it needs
next. The end result from this codelab combines dynamically selected agent
actions with the durable execution, suspension, and resumption cycle of a saga.

## Further Explorations: Beyond This Codelab

Here are a few ways you can continue expanding on the concepts covered in this
codelab.

### Process More Emails

We currently derive a small, fixed set of email addresses from the hardcoded
user IDs. Consider supplying a larger data set from a file, input generator, or
external API. Then create _hundreds_ of dynamic branches to observe how
Conductor schedules tasks, manages worker throughput, and joins results under
load.

### Migrate to a Cloud Database

We use SQLite to keep this codelab simple and self-contained. Consider replacing
it with a more advanced cloud-based platform such as
[Databricks](https://docs.databricks.com/aws/en/) or
[Snowflake](https://docs.snowflake.com/en/user-guide/databases). This will let
you handle larger data sets and allow for shared data access while keeping your
data storage layer separate from the agent runtime.

### Add More Summarizing Agents

In Exercise 3, we use a single agent to summarize all email activity. Consider
dividing the analysis among specialized agents by recipient, subject, or time
period, then using a coordinating agent to combine their findings into a single
digest. This will let you explore parallel agent collaboration and the advanced
scaling needed to process more email traffic.
