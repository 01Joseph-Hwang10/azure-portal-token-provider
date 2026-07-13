# azure-portal-token-provider

This application provides a simple way to obtain an Azure Portal access token via API-Key protected REST API via Playwright automated access token retrieval from the session storage.

## Motivation

If you're building an application that needs to interact with Azure Graph API, you may need to obtain an access token used in Azure Portal Dashboard. This token is highly privileged and can be used to access various Azure resources which cannot be accessed by common subscription scoped tokens, but this token cannot be retrieved directly via `az` cli unless if you're a global adminstrator of the Azure tenant.

Since Azure wants you to pay for at least P1 license of MS Entra ID (which is $84 per year, quite expensive) to be able to create another tenant and become a global administrator (in case you're already in an existing tenant such as your school or work, and you cannot leave it by yourself), this application provides a way to retrieve highly privileged access token from Azure Portal without the need of being a global administrator so you can act as a highly privileged user programmatically.
