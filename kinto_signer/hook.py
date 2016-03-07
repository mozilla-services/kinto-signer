from cliquet.events import ResourceChanged

from kinto_signer import utils
from kinto_signer.updater import LocalUpdater
from kinto_signer.signer.remote import AutographSigner


def includeme(config):
    # Process settings to remove storage wording.
    settings = config.get_settings()

    config.registry.signer = AutographSigner(settings)

    raw_resources = settings.get('kinto_signer.resources')
    if raw_resources is None:
        raise ValueError("Please specify the kinto_signer.resources value.")
    available_resources = utils.parse_resources(raw_resources)

    message = "Provide signing capabilities to the server."
    docs = "https://github.com/mozilla-services/kinto-signer#kinto-signer"
    resources = sorted(available_resources.keys())
    config.add_api_capability("signer", message, docs,
                              resources=resources)

    def on_resource_changed(event):
        payload = event.payload
        requested_resource = "{bucket_id}/{collection_id}".format(**payload)
        if requested_resource not in available_resources:
            return

        resource = available_resources.get(requested_resource)
        should_sign = any([True for r in event.impacted_records
                           if r['new'].get('status') == 'to-sign'])
        if should_sign:
            registry = event.request.registry
            updater = LocalUpdater(
                signer=registry.signer,
                storage=registry.storage,
                permission=registry.permission,
                source=resource['source'],
                destination=resource['destination'])

            updater.sign_and_update_remote()

    config.add_subscriber(
        on_resource_changed,
        ResourceChanged,
        for_actions=('create', 'update'),
        for_resources=('collection',)
    )
