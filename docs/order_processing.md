# Webhooks

* MAKE SURE TO LOGIN&#x20;
*
* stripe login and press return (only works on Chrome)
* stripe listen --forward-to localhost:8000/lessons\_payment/webhook/
* can use the same webhook.py file for all. To do this you must send the order type as metadata and this will be returned in the webhook and you can select the correct Order to update from that information.
