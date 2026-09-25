# Long Running Sagas

Experimental directory for agentic processes that take a long time (eg: on the order of days, at minimum) to execute.

## Setup

Each codelab can be completed in one or more programming languages, and each language version lists its own requirements in its README. All of them read your Orkes Conductor server URL, credentials and other account details from a `.env` file at the top level of this repository, so you only need to enter them once.

[Create an application access key](https://orkes.io/content/access-control-and-security/applications) in the Orkes Conductor UI under Access Control > Applications. Then copy the example settings file:

```bash
cp .env.example .env
```

Set the following values in `.env` before running any code:

```bash
CONDUCTOR_SERVER_URL=https://developer.orkescloud.com/api
CONDUCTOR_AUTH_KEY=your_key_id
CONDUCTOR_AUTH_SECRET=your_key_secret
```

Replace the server URL with your own cluster's URL if you are not using the free developer edition. Each codelab's README explains the remaining values in `.env`. Any of these variables that you export in your shell take precedence over the values in `.env`.

## Codelabs

| Codelab | Languages |
| --- | --- |
| [Webhooks](webhooks/README.md) | [Python](webhooks/python/README.md), [C#](webhooks/csharp/README.md) |

### Webhooks

This interactive codelab will teach you how to use a `WAIT_FOR_WEBHOOK` task to resume an in-progress workflow after suspending its execution for up to 7 days. It is an implementation of the concepts mentioned [in this blog post from our CTO, Viren Baraiya](https://orkes.io/blog/late-bound-sagas-why-your-agent-is-not-an-llm-in-a-loop#what-it-looks-like-in-motion).

Start with [the codelab's README](webhooks/README.md), then follow the setup steps for your chosen language.
