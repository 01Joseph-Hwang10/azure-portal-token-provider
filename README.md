# azure-portal-token-provider

This application provides a simple way to obtain an Azure Portal access token via API-Key protected REST API via Playwright automated access token retrieval from the session storage.

## Motivation

If you're building an application that needs to interact with Azure Graph API, you may need to obtain an access token used in Azure Portal Dashboard. This token is highly privileged and can be used to access various Azure resources which cannot be accessed by common subscription scoped tokens, but this token cannot be retrieved directly via `az` cli unless if you're a global adminstrator of the Azure tenant.

Since Azure wants you to pay for at least P1 license of MS Entra ID (which is $84 per year, quite expensive) to be able to create another tenant and become a global administrator (in case you're already in an existing tenant such as your school or work, and you cannot leave it by yourself), this application provides a way to retrieve highly privileged access token from Azure Portal without the need of being a global administrator so you can act as a highly privileged user programmatically.

## Usage

I planned this to run on my spare windows laptop as a development mode and make it accessible through the internet via Cloudflare Quick tunnel, so this section is written with that in mind. If you want to run this on the cloud like AWS, you may need to do the extra job such as writing a `Dockerfile` and setting up a reverse proxy to make it accessible via the internet.

### Prerequisites

- `git`
- `python` 3.13 or higher
- `uv` package manager
- `cloudflared` for Cloudflare Quick Tunnel

### Install & Run

```bash
# Clone this repository
git clone https://github.com/01Joseph-Hwang10/azure-portal-token-provider
cd azure-portal-token-provider

# Install dependencies
uv sync

# Install firefox for playwright
uv run playwright install firefox

# Set your API key to protect the endpoint.
# If not set, the endpoint will be unprotected and anyone can access it.
export API_KEY="<your-api-key>"

# Start the server
uv run python -m src.app

# Run cloudflare quick tunnel to make it accessible via the internet
cloudflared tunnel --url http://localhost:8000
```

### Login to Azure Portal

When you first run the server, playwright browser will be launched and it will stop on the login page of Azure Portal.
This is a manual step that should be done by the user, and it's required only once unless the server is restarted for unknown reasons.
After you login, the server will automatically retrieve the access token from the session storage and store it in memory.

### Retrieve Access Token

You can retrieve the access token by sending a GET request to the `/token` endpoint with your API key in the `X-Api-Key` header.

```bash
curl -H "X-Api-Key: <your-api-key>" https://<your-domain>/token
```

It will then return a JSON response like this:

```json
{
  "token": "<your-access-token>",
  "expires_at": "<token-expiration-time-in-iso-format>"
}
```

If the token is expired or not available for some reason, it will return:

```json
{
  "token": null,
  "expires_at": null
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
